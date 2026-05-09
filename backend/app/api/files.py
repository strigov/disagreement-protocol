from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.services.storage import S3Storage

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{document_id}/input.docx")
def download_input(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    data = S3Storage().get(doc.storage_key)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
