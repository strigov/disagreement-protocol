from __future__ import annotations

import uuid
import re
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.clause import Clause as ClauseModel
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.protocol import Protocol, ProtocolRow
from app.processing.types import (
    Clause as ClauseDC,
    EnrichedParagraph,
    RawParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
    RevisionRecord,
    Run,
)
from app.processing.validation_engine import ValidationEngine
from app.schemas.protocol import ExportRequest, ProtocolOut, ProtocolRowCreate, ProtocolRowOut, ProtocolRowPatch
from app.services.exporter import ProtocolExporter
from app.services.protocol_generator import BuildContext, ProtocolRowBuilder, agreed_text_for_party

router = APIRouter(prefix="/api", tags=["protocols"])

_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    " ": "_",
}


def _sanitize_filename(name: str) -> str:
    sanitized = name.strip().replace("/", "").replace("\\", "")
    sanitized = re.sub(r"[\x00-\x1f\x7f]", "", sanitized)
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or "Протокол_разногласий"


def _ascii_fallback(name: str) -> str:
    out = []
    for char in name:
        lower = char.lower()
        if lower in _TRANSLIT:
            translit = _TRANSLIT[lower]
            out.append(translit if char == lower else translit.capitalize())
        elif char.isascii() and (char.isalnum() or char in "._-"):
            out.append(char)
        else:
            out.append("_")
    result = "".join(out).strip("_")
    return result or "protocol"


def _serialize_row(row: ProtocolRow) -> ProtocolRowOut:
    return ProtocolRowOut(
        id=row.id,
        sort_order=row.sort_order,
        point_label=row.point_label,
        party_1_text=row.party_1_text,
        party_2_text=row.party_2_text,
        agreed_text=row.agreed_text,
        source_clause_key=row.source_clause_key,
        confidence=row.confidence,
        flags=list(row.flags),
        user_edited=row.user_edited,
    )


@router.post("/documents/{document_id}/protocol", response_model=ProtocolOut, status_code=201)
def build_protocol(document_id: uuid.UUID, db: Session = Depends(get_db)) -> ProtocolOut:
    result = db.execute(select(Document).where(Document.id == document_id).with_for_update())
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(404, "Document not found")
    if doc.drafting_party_id is None:
        raise HTTPException(409, "Drafting party not set")

    parties = db.query(Party).filter(Party.document_id == document_id).all()
    if len(parties) != 2:
        raise HTTPException(409, "MVP supports exactly two parties")

    drafting = next((p for p in parties if p.id == doc.drafting_party_id), None)
    counterparty = next((p for p in parties if p.id != doc.drafting_party_id), None)
    if drafting is None or counterparty is None:
        raise HTTPException(409, "Drafting party not found")

    clause_models = (
        db.query(ClauseModel)
        .filter(ClauseModel.document_id == document_id)
        .order_by(ClauseModel.sort_order)
        .all()
    )
    clauses_dc: list[ClauseDC] = []
    for cm in clause_models:
        clause = ClauseDC(clause_key=cm.clause_key, label=cm.label, level=cm.level, parent_key=cm.parent_key)
        clause.flags = set(cm.flags or [])
        clause.paragraphs.append(
            EnrichedParagraph(
                block_id=cm.clause_key,
                text_runs=cm.accepted_text,
                num_id=None,
                ilvl=cm.level,
                original_text=cm.original_text,
                accepted_text=cm.accepted_text,
                revisions=tuple(
                    RevisionRecord(type=r.get("type", ""), text=r.get("text", ""), author=r.get("author", ""))
                    for r in (cm.revisions or [])
                ),
                rendered_number=cm.label,
                numbering_confidence=cm.confidence,
            ),
        )
        for table in cm.tables_json or []:
            rows_dc: list[RawTableRow] = []
            for row_cells in table.get("rows", []):
                cells = tuple(
                    RawTableCell(
                        paragraphs=(
                            RawParagraph(
                                block_id=f"{table['block_id']}_p_{index:04d}",
                                runs=(Run(text=cell_text or ""),),
                                num_id=None,
                                ilvl=None,
                                style_id=None,
                                is_in_table=True,
                            ),
                        ),
                    )
                    for index, cell_text in enumerate(row_cells)
                )
                rows_dc.append(RawTableRow(cells=cells))
            clause.tables.append(
                RawTable(
                    block_id=table["block_id"],
                    block_index=0,
                    rows=tuple(rows_dc),
                    has_revisions=bool(table.get("has_revisions", False)),
                ),
            )
        clauses_dc.append(clause)

    changed = [
        clause
        for clause in clauses_dc
        if any(revision.type in ("INS", "DEL") for paragraph in clause.paragraphs for revision in paragraph.revisions)
        or any(table.has_revisions for table in clause.tables)
        or "STANDALONE_TABLE" in clause.flags
    ]
    ctx = BuildContext(drafting_party_role=drafting.role, counterparty_role=counterparty.role)
    built = ProtocolRowBuilder().build(changed, ctx)

    existing_protocols = db.query(Protocol).filter(Protocol.document_id == document_id).all()
    for existing_protocol in existing_protocols:
        db.query(ProtocolRow).filter(ProtocolRow.protocol_id == existing_protocol.id).delete(synchronize_session=False)
    db.query(Protocol).filter(Protocol.document_id == document_id).delete()

    protocol = Protocol(document_id=document_id)
    db.add(protocol)
    db.flush()

    persisted_rows: list[ProtocolRow] = []
    for idx, built_row in enumerate(built):
        protocol_row = ProtocolRow(
            protocol_id=protocol.id,
            sort_order=idx,
            point_label=built_row.point_label,
            party_1_text=built_row.party_1_text,
            party_2_text=built_row.party_2_text,
            agreed_text=built_row.agreed_text,
            source_clause_key=built_row.source_clause_key,
            confidence=built_row.confidence,
            flags=built_row.flags,
            user_edited=False,
        )
        db.add(protocol_row)
        persisted_rows.append(protocol_row)

    db.flush()
    for built_row, protocol_row in zip(built, persisted_rows):
        built_row.row_id = str(protocol_row.id)

    from app.processing.types import ResolverDiagnostic

    diagnostics_raw = ((doc.metadata_json or {}).get("preflight_diagnostics") or [])
    resolver_diagnostics = [
        ResolverDiagnostic(
            level=diagnostic.get("level", "warning"),
            component=diagnostic.get("component", ""),
            code=diagnostic.get("code", "MAPPING_MISMATCH"),
            message=diagnostic.get("message", ""),
            block_id=diagnostic.get("block_id"),
        )
        for diagnostic in diagnostics_raw
    ]
    report = ValidationEngine().validate(built, clauses_dc, resolver_diagnostics)
    doc.validation_report = {
        "textual_revisions_total": report.textual_revisions_total,
        "format_only_revisions": report.format_only_revisions,
        "covered_revisions": report.covered_revisions,
        "numbering_confidence_mean": report.numbering_confidence_mean,
        "warnings": report.warnings,
    }
    doc.status = DocumentStatus.BUILT
    db.commit()

    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol.id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    return ProtocolOut(id=protocol.id, document_id=document_id, rows=[_serialize_row(row) for row in rows])


@router.patch("/protocols/{protocol_id}/rows/{row_id}", response_model=ProtocolRowOut)
def patch_row(
    protocol_id: uuid.UUID,
    row_id: uuid.UUID,
    payload: ProtocolRowPatch,
    db: Session = Depends(get_db),
) -> ProtocolRowOut:
    row = db.get(ProtocolRow, row_id)
    if row is None or row.protocol_id != protocol_id:
        raise HTTPException(404, "Row not found")

    if payload.merge_with in ("previous", "next"):
        siblings = (
            db.query(ProtocolRow)
            .filter(ProtocolRow.protocol_id == protocol_id)
            .order_by(ProtocolRow.sort_order)
            .all()
        )
        index = next((i for i, candidate in enumerate(siblings) if candidate.id == row.id), -1)
        target = None
        if payload.merge_with == "previous" and index > 0:
            target = siblings[index - 1]
        elif payload.merge_with == "next" and 0 <= index < len(siblings) - 1:
            target = siblings[index + 1]
        if target is None:
            raise HTTPException(409, "No neighbouring row to merge with")

        for column in ("party_1_text", "party_2_text", "agreed_text"):
            existing = getattr(target, column) or ""
            extra = getattr(row, column) or ""
            setattr(target, column, f"{existing}\n{extra}".strip("\n"))
        target.user_edited = True
        if "USER_EDITED" not in (target.flags or []):
            target.flags = [*list(target.flags or []), "USER_EDITED"]
        db.delete(row)
        db.commit()
        return _serialize_row(target)

    for column in ("point_label", "party_1_text", "party_2_text", "agreed_text"):
        value = getattr(payload, column)
        if value is not None:
            setattr(row, column, value)
    row.user_edited = True
    if "USER_EDITED" not in (row.flags or []):
        row.flags = [*list(row.flags or []), "USER_EDITED"]
    db.commit()
    return _serialize_row(row)


@router.post("/documents/{document_id}/protocol/export")
def export_protocol(
    document_id: uuid.UUID,
    payload: ExportRequest,
    db: Session = Depends(get_db),
) -> Response:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    parties = db.query(Party).filter(Party.document_id == document_id).all()
    drafting = next((party for party in parties if party.id == doc.drafting_party_id), None)
    counterparty = next((party for party in parties if party.id != doc.drafting_party_id), None) if drafting else None
    if drafting is None or counterparty is None:
        raise HTTPException(409, "Parties not finalized")

    protocol = db.query(Protocol).filter(Protocol.document_id == document_id).one_or_none()
    if protocol is None:
        raise HTTPException(409, "Protocol not built")

    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol.id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    payload_rows = [
        {
            "point_label": row.point_label,
            "party_1_text": row.party_1_text,
            "party_2_text": row.party_2_text,
            "agreed_text": row.agreed_text,
        }
        for row in rows
    ]
    data = ProtocolExporter().export(payload_rows, drafting.role, counterparty.role, doc.contract_name)
    name = _sanitize_filename(payload.filename)
    ascii_name = _ascii_fallback(name) + ".docx"
    utf8_name = urllib.parse.quote(name + ".docx", safe="")
    headers = {
        "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8_name}",
    }
    doc.status = DocumentStatus.EXPORTED
    db.commit()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@router.post("/protocols/{protocol_id}/rows", response_model=ProtocolRowOut, status_code=201)
def add_row(
    protocol_id: uuid.UUID,
    payload: ProtocolRowCreate,
    db: Session = Depends(get_db),
) -> ProtocolRowOut:
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")

    existing = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    insert_at = payload.sort_order if payload.sort_order is not None else len(existing)
    insert_at = max(0, min(insert_at, len(existing)))
    for row in existing:
        if row.sort_order >= insert_at:
            row.sort_order += 1

    new_row = ProtocolRow(
        protocol_id=protocol_id,
        sort_order=insert_at,
        point_label="",
        party_1_text="",
        party_2_text="",
        agreed_text="",
        source_clause_key=None,
        confidence=1.0,
        flags=["MANUALLY_ADDED"],
        user_edited=True,
    )
    db.add(new_row)
    db.commit()
    return _serialize_row(new_row)


@router.delete("/protocols/{protocol_id}/rows/{row_id}", status_code=204, response_class=Response)
def delete_row(
    protocol_id: uuid.UUID,
    row_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Response:
    row = db.get(ProtocolRow, row_id)
    if row is None or row.protocol_id != protocol_id:
        raise HTTPException(404, "Row not found")

    deleted_order = row.sort_order
    db.delete(row)
    rest = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id, ProtocolRow.sort_order > deleted_order)
        .all()
    )
    for rest_row in rest:
        rest_row.sort_order -= 1
    db.commit()
    return Response(status_code=204)


@router.get("/protocols/{protocol_id}/rows", response_model=ProtocolOut)
def get_protocol_rows(
    protocol_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ProtocolOut:
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")
    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    return ProtocolOut(
        id=protocol.id,
        document_id=protocol.document_id,
        rows=[_serialize_row(row) for row in rows],
    )


@router.get("/protocols", response_model=list[ProtocolOut])
def list_protocols_for_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[ProtocolOut]:
    protocols = db.query(Protocol).filter(Protocol.document_id == document_id).all()
    out: list[ProtocolOut] = []
    for protocol in protocols:
        rows = (
            db.query(ProtocolRow)
            .filter(ProtocolRow.protocol_id == protocol.id)
            .order_by(ProtocolRow.sort_order)
            .all()
        )
        out.append(
            ProtocolOut(
                id=protocol.id,
                document_id=protocol.document_id,
                rows=[_serialize_row(row) for row in rows],
            ),
        )
    return out


@router.post("/protocols/{protocol_id}/swap-parties", response_model=ProtocolOut)
def swap_parties(
    protocol_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ProtocolOut:
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")

    doc = db.get(Document, protocol.document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    parties = db.query(Party).filter(Party.document_id == doc.id).all()
    if len(parties) != 2:
        raise HTTPException(409, "Swap requires exactly two parties")

    old_drafting = next((party for party in parties if party.id == doc.drafting_party_id), None)
    other = next((party for party in parties if party.id != doc.drafting_party_id), None)
    if old_drafting is None or other is None:
        raise HTTPException(409, "Drafting party not set")

    new_agreed = agreed_text_for_party(other.role)
    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    for row in rows:
        if not row.user_edited:
            row.agreed_text = new_agreed
    doc.drafting_party_id = other.id
    db.commit()
    return ProtocolOut(
        id=protocol.id,
        document_id=protocol.document_id,
        rows=[_serialize_row(row) for row in rows],
    )
