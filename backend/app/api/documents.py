from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.schemas.document import DocumentCreated
from app.services.ingestion import MAX_BYTES, IngestError, derive_contract_name, validate_upload
from app.services.storage import S3Storage
from app.workers.tasks import process_document

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentCreated, status_code=201)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentCreated:
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
    S3Storage().put(storage_key, data)
    doc = Document(
        id=doc_id,
        original_filename=filename or "document.docx",
        storage_key=storage_key,
        contract_name=derive_contract_name(filename),
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    process_document.delay(str(doc_id))
    return DocumentCreated(id=doc_id, status=doc.status.value)
