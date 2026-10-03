from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException
from python_multipart.exceptions import MultipartParseError

from app.api.upload_form import SingleFileParser, UploadLimitError

from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.protocol import Protocol, ProtocolRow
from app.schemas.document import AnalysisOut, DocumentCreated, PreflightDiagnostic, PreflightMetrics
from app.schemas.party import PartiesUpdateIn, PartyOut
from app.schemas.validation import ValidationReportOut
from app.services.ingestion import MAX_BYTES, IngestError, derive_contract_name, validate_upload
from app.services.processing import process_document
from app.services.protocol_state import refresh_validation, synchronize_agreed
from app.services.storage import FileStorage

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentCreated, status_code=201)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DocumentCreated:
    # Explicit limits apply before a dependency/automatic File parser can run.
    try:
        form = await SingleFileParser(request.headers, request.stream(), MAX_BYTES).parse()
    except UploadLimitError as exc:
        raise HTTPException(413, exc.message) from exc
    except (MultiPartException, MultipartParseError) as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        file = form.get("file")
        if len(form.multi_items()) != 1 or not isinstance(file, UploadFile):
            raise HTTPException(400, "Выберите один файл договора.")
        return await run_in_threadpool(_store_upload, file, background_tasks, db)
    finally:
        await form.close()


def _store_upload(file: UploadFile, background_tasks: BackgroundTasks, db: Session) -> DocumentCreated:
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .docx без макросов")

    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Размер файла превышает 25 МБ")

    try:
        validate_upload(filename, data)
    except IngestError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc

    doc_id = uuid.uuid4()
    storage_key = f"documents/{doc_id}/input.docx"
    FileStorage().put(storage_key, data)
    doc = Document(
        id=doc_id,
        original_filename=filename or "document.docx",
        storage_key=storage_key,
        contract_name=derive_contract_name(filename),
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    background_tasks.add_task(process_document, str(doc_id))
    return DocumentCreated(id=doc_id, status=doc.status.value)


@router.get("/{document_id}/analysis", response_model=AnalysisOut)
def get_analysis(document_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisOut:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Договор не найден. Откройте исходный файл заново.")

    parties = db.query(Party).filter(Party.document_id == document_id).all()
    if doc.validation_report is not None:
        refresh_validation(db, doc)
    diagnostics_raw = ((doc.metadata_json or {}).get("preflight_diagnostics") or [])
    return AnalysisOut(
        id=doc.id,
        status=doc.status.value,
        error_message=doc.error_message,
        contract_name=doc.contract_name,
        preflight_metrics=PreflightMetrics(**doc.preflight_metrics) if doc.preflight_metrics else None,
        preflight_diagnostics=[PreflightDiagnostic(**diagnostic) for diagnostic in diagnostics_raw],
        parties=[
            PartyOut(id=party.id, name=party.name, role=party.role, confidence=party.confidence)
            for party in parties
        ],
        validation_report=ValidationReportOut(**doc.validation_report) if doc.validation_report else None,
        drafting_party_id=doc.drafting_party_id,
    )


@router.patch("/{document_id}/parties", response_model=AnalysisOut)
def update_parties(
    document_id: uuid.UUID,
    payload: PartiesUpdateIn,
    db: Session = Depends(get_db),
) -> AnalysisOut:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Договор не найден. Откройте исходный файл заново.")

    existing = {party.id: party for party in db.query(Party).filter(Party.document_id == document_id).all()}
    if len(payload.parties) != 2:
        raise HTTPException(status_code=422, detail="Укажите две стороны договора.")

    existing_payload_ids = [item.id for item in payload.parties if item.id is not None and item.id in existing]
    if len(existing_payload_ids) != len(set(existing_payload_ids)):
        raise HTTPException(status_code=422, detail="Одна сторона указана дважды. Выберите две разные стороны договора.")

    drafting_party = existing.get(payload.drafting_party_id) if payload.drafting_party_id is not None else None
    if payload.drafting_party_id is not None:
        drafting_party_matches = any(
            drafting_party is not None
            and item.id == payload.drafting_party_id
            for item in payload.parties
        )
        if not drafting_party_matches:
            raise HTTPException(
                status_code=422,
                detail="Выберите вашу сторону из указанных сторон договора.",
            )

    if payload.drafting_party_id is None:
        doc.drafting_party_id = None

    seen_ids: set[uuid.UUID] = set()
    for item in payload.parties:
        if item.id and item.id in existing:
            existing[item.id].name = item.name
            existing[item.id].role = item.role
            seen_ids.add(item.id)
        else:
            db.add(Party(document_id=document_id, name=item.name, role=item.role, confidence=1.0))

    for party_id, party in existing.items():
        if party_id not in seen_ids:
            db.delete(party)

    if payload.drafting_party_id is not None:
        doc.drafting_party_id = payload.drafting_party_id
        for protocol in db.query(Protocol).filter(Protocol.document_id == document_id).all():
            rows = db.query(ProtocolRow).filter(ProtocolRow.protocol_id == protocol.id).all()
            synchronize_agreed(rows, existing[payload.drafting_party_id].role)
        if doc.status == DocumentStatus.EXPORTED:
            doc.status = DocumentStatus.BUILT
        elif doc.status != DocumentStatus.BUILT:
            doc.status = DocumentStatus.PARTIES_CONFIRMED

    db.commit()
    return get_analysis(document_id, db)
