from __future__ import annotations

import uuid
from datetime import datetime

from app.db.session import SessionLocal
from app.models.clause import Clause as ClauseModel
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.services.ingestion import run_pipeline
from app.services.storage import S3Storage
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.process_document")
def process_document(document_id: str) -> None:
    storage = S3Storage()
    db = SessionLocal()
    try:
        doc = db.get(Document, uuid.UUID(document_id))
        if doc is None:
            return

        doc.status = DocumentStatus.PARSING
        db.commit()
        try:
            data = storage.get(doc.storage_key)
            result = run_pipeline(data)
        except Exception as exc:  # noqa: BLE001
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(exc)[:2000]
            db.commit()
            return

        for idx, clause in enumerate(result["clauses"]):
            db.add(
                ClauseModel(
                    document_id=doc.id,
                    clause_key=clause.clause_key,
                    label=clause.label,
                    level=clause.level,
                    parent_key=clause.parent_key,
                    sort_order=idx,
                    original_text="\n".join(paragraph.original_text for paragraph in clause.paragraphs),
                    accepted_text="\n".join(paragraph.accepted_text for paragraph in clause.paragraphs),
                    flags=sorted(clause.flags),
                    confidence=1.0,
                    revisions=[
                        {"type": revision.type, "text": revision.text, "author": revision.author}
                        for paragraph in clause.paragraphs
                        for revision in paragraph.revisions
                    ],
                    tables_json=[
                        {
                            "block_id": table.block_id,
                            "has_revisions": table.has_revisions,
                            "rows": [[cell.text() for cell in row.cells] for row in table.rows],
                        }
                        for table in clause.tables
                    ],
                )
            )

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
        doc.metadata_json = {"preflight_diagnostics": result["preflight_diagnostics"]}
        doc.status = DocumentStatus.PARSED
        doc.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
