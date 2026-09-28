"""Shared invariants for protocol mutations, validation, and party changes."""
from dataclasses import asdict

from app.models.clause import Clause as ClauseModel
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.protocol import Protocol, ProtocolRow
from app.processing.types import ResolverDiagnostic
from app.processing.validation_engine import ValidationEngine
from app.services.clause_codec import restore_clause
from app.services.protocol_generator import BuiltRow, agreed_text_for_party


def source_keys(row: ProtocolRow) -> list[str]:
    return list(dict.fromkeys(row.source_clause_keys or ([row.source_clause_key] if row.source_clause_key else [])))


def agreed_was_edited(row: ProtocolRow) -> bool:
    return row.agreed_text_edited if row.agreed_text_edited is not None else bool(row.user_edited)


def synchronize_agreed(rows: list[ProtocolRow], role: str) -> None:
    for row in rows:
        if not agreed_was_edited(row):
            row.agreed_text = agreed_text_for_party(role)


def normalize_order(rows: list[ProtocolRow]) -> None:
    for index, row in enumerate(rows):
        row.sort_order = index


def refresh_validation(db, doc: Document, rows=None, clauses=None) -> dict:
    if rows is None:
        protocols = db.query(Protocol).filter(Protocol.document_id == doc.id).all()
        rows = [row for protocol in protocols for row in
                db.query(ProtocolRow).filter(ProtocolRow.protocol_id == protocol.id).all()]
    if clauses is None:
        clauses = [restore_clause(c) for c in
                   db.query(ClauseModel).filter(ClauseModel.document_id == doc.id).order_by(ClauseModel.sort_order).all()]
    built = [BuiltRow(
        point_label=row.point_label, party_1_text=row.party_1_text, party_2_text=row.party_2_text,
        agreed_text=row.agreed_text, source_clause_key=row.source_clause_key,
        source_clause_keys=source_keys(row), confidence=row.confidence,
        flags=list(row.flags or []), row_id=str(row.id),
    ) for row in rows]
    diagnostics = [ResolverDiagnostic(
        level=d.get("level", "warning"), component=d.get("component", ""),
        code=d.get("code", "MAPPING_MISMATCH"), message=d.get("message", ""), block_id=d.get("block_id"),
    ) for d in ((doc.metadata_json or {}).get("preflight_diagnostics") or [])]
    doc.validation_report = asdict(ValidationEngine().validate(built, clauses, diagnostics))
    return doc.validation_report


def refresh_for_protocol(db, protocol_id) -> None:
    protocol = db.get(Protocol, protocol_id)
    if protocol is not None:
        doc = db.get(Document, protocol.document_id)
        if doc is not None:
            db.flush()
            refresh_validation(db, doc)
            if doc.status == DocumentStatus.EXPORTED:
                doc.status = DocumentStatus.BUILT
