from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.schemas.document import AnalysisOut, DocumentCreated, PreflightDiagnostic, PreflightMetrics
from app.schemas.party import PartiesUpdateIn, PartyOut
from app.schemas.validation import ValidationReportOut
from app.services.ingestion import MAX_BYTES, IngestError, derive_contract_name, validate_upload
from app.services.processing import process_document
from app.services.storage import FileStorage

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentCreated, status_code=201)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentCreated:
    filename = file.filename or ""
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .docx без макросов")

    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Размер файла превышает 25 MB")

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
        raise HTTPException(status_code=404, detail="Document not found")

    parties = db.query(Party).filter(Party.document_id == document_id).all()
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
        raise HTTPException(status_code=404, detail="Document not found")

    existing = {party.id: party for party in db.query(Party).filter(Party.document_id == document_id).all()}
    if len(payload.parties) != 2:
        raise HTTPException(status_code=422, detail="Exactly 2 parties are required")

    existing_payload_ids = [item.id for item in payload.parties if item.id is not None and item.id in existing]
    if len(existing_payload_ids) != len(set(existing_payload_ids)):
        raise HTTPException(status_code=422, detail="Duplicate party ids in payload")

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
                detail="drafting_party_id must reference one of the confirmed parties",
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
        doc.status = DocumentStatus.PARTIES_CONFIRMED

    db.commit()
    return get_analysis(document_id, db)
