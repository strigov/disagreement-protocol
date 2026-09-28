from __future__ import annotations

import logging
import uuid
from threading import BoundedSemaphore
from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.services.ingestion import run_pipeline
from app.services.clause_codec import serialize_clause
from app.services.storage import FileStorage


_processing_slot = BoundedSemaphore(1)
logger = logging.getLogger(__name__)


def process_document(document_id: str) -> None:
    with _processing_slot:
        _process_document(document_id)


def _process_document(document_id: str) -> None:
    """Run the OOXML pipeline for an uploaded document.

    Executed as a FastAPI background task after the upload response is sent;
    opens its own DB session because the request session is already closed.
    """
    db = None
    try:
        db = SessionLocal()
        doc = db.get(Document, uuid.UUID(document_id))
        if doc is None or doc.status != DocumentStatus.UPLOADED:
            return

        doc.status = DocumentStatus.PARSING
        db.commit()
        data = FileStorage().get(doc.storage_key)
        result = run_pipeline(data)

        for idx, clause in enumerate(result["clauses"]):
            db.add(serialize_clause(clause, doc.id, idx))

        for party in result["parties"]:
            db.add(
                Party(
                    document_id=doc.id,
                    name=party.name,
                    role=party.role,
                    confidence=party.confidence,
                )
            )

        doc.preflight_metrics = result["preflight_metrics"]
        doc.metadata_json = {"pipeline_version": 2, "preflight_diagnostics": result["preflight_diagnostics"]}
        doc.status = DocumentStatus.PARSED
        doc.error_message = None
        doc.updated_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document processing failed: %s", document_id)
        if db is not None:
            try:
                db.rollback()
            except Exception:  # noqa: BLE001
                logger.exception("Could not roll back processing transaction: %s", document_id)
        # A separate transaction survives a failed flush/commit of parsed content.
        try:
            failure_db = SessionLocal()
            try:
                doc = failure_db.get(Document, uuid.UUID(document_id))
                if doc is not None and doc.status in (DocumentStatus.UPLOADED, DocumentStatus.PARSING):
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = str(exc)[:2000] or "Ошибка обработки документа"
                    doc.updated_at = datetime.now(UTC)
                    failure_db.commit()
            finally:
                failure_db.close()
        except Exception:  # noqa: BLE001
            logger.exception("Could not persist processing failure: %s", document_id)
    finally:
        if db is not None:
            db.close()


def recover_interrupted_documents(db) -> int:
    """On a single-process local startup no queued/working task can still be alive."""
    documents = db.query(Document).filter(
        Document.status.in_([DocumentStatus.UPLOADED, DocumentStatus.PARSING])
    ).all()
    for doc in documents:
        doc.status = DocumentStatus.FAILED
        doc.error_message = "Обработка прервана перезапуском приложения. Загрузите документ повторно."
        doc.updated_at = datetime.now(UTC)
    db.commit()
    return len(documents)
