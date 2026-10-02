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
from app.processing.ooxml_parser import OOXMLParser
from app.schemas.protocol import ExportRequest, ProtocolOut, ProtocolRowCreate, ProtocolRowOut, ProtocolRowPatch
from app.schemas.protocol_form import ProtocolForm, ProtocolFormPatch
from app.services.protocol_form import apply_form_patch, resolve_form
from app.services.exporter import ProtocolExporter
from app.services.protocol_generator import BuildContext, ProtocolRowBuilder
from app.services.clause_codec import restore_clause
from app.services.storage import FileStorage
from app.services.protocol_state import (
    agreed_was_edited, normalize_order, refresh_for_protocol, refresh_validation,
    source_keys, synchronize_agreed,
)

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


def _serialize_protocol(db: Session, protocol: Protocol, rows: list[ProtocolRow]) -> ProtocolOut:
    doc = db.get(Document, protocol.document_id)
    parties = db.query(Party).filter(Party.document_id == protocol.document_id).all()
    return ProtocolOut(
        id=protocol.id, document_id=protocol.document_id,
        rows=[_serialize_row(row) for row in rows],
        form=resolve_form(protocol, doc, parties),
    )


@router.patch("/protocols/{protocol_id}/form", response_model=ProtocolForm)
def patch_form(protocol_id: uuid.UUID, payload: ProtocolFormPatch, db: Session = Depends(get_db)) -> ProtocolForm:
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")
    doc = db.get(Document, protocol.document_id)
    parties = db.query(Party).filter(Party.document_id == protocol.document_id).all()
    if payload.signatures and not set(payload.signatures).issubset({party.id for party in parties}):
        raise HTTPException(422, "Подпись должна относиться к стороне этого договора")
    apply_form_patch(protocol, payload)
    form = resolve_form(protocol, doc, parties)
    if doc.status == DocumentStatus.EXPORTED:
        doc.status = DocumentStatus.BUILT
    db.commit()
    return form


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
    clauses_dc = [restore_clause(cm) for cm in clause_models]
    if any("SOURCE_ORDER_UNAVAILABLE" in clause.flags for clause in clauses_dc):
        try:
            raw = OOXMLParser().parse(FileStorage().get(doc.storage_key))
        except (OSError, ValueError):
            # Keep the explicit legacy warning if the original file is unavailable.
            pass
        else:
            order = {block.block_id: block.block_index for block in raw.blocks}
            for model in clause_models:
                if model.paragraphs_json is not None:
                    model.paragraphs_json = [
                        {**p, "block_index": p["block_index"] if p.get("block_index") is not None
                         else order.get(p.get("block_id"))}
                        for p in model.paragraphs_json
                    ]
                model.tables_json = [
                    {**table, "block_index": table["block_index"] if table.get("block_index") is not None
                     else order.get(table.get("block_id"))}
                    for table in (model.tables_json or [])
                ]
            clauses_dc = [restore_clause(cm) for cm in clause_models]

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
    saved_form = existing_protocols[0].form_json if existing_protocols else None
    for existing_protocol in existing_protocols:
        db.query(ProtocolRow).filter(ProtocolRow.protocol_id == existing_protocol.id).delete(synchronize_session=False)
    db.query(Protocol).filter(Protocol.document_id == document_id).delete()

    protocol = Protocol(document_id=document_id, form_json=saved_form)
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
            source_clause_keys=[built_row.source_clause_key] if built_row.source_clause_key else [],
            agreed_text_edited=False,
            confidence=built_row.confidence,
            flags=built_row.flags,
            user_edited=False,
        )
        db.add(protocol_row)
        persisted_rows.append(protocol_row)

    db.flush()
    for built_row, protocol_row in zip(built, persisted_rows):
        built_row.row_id = str(protocol_row.id)

    refresh_validation(db, doc, persisted_rows, clauses_dc)
    doc.status = DocumentStatus.BUILT
    db.commit()

    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol.id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    return _serialize_protocol(db, protocol, rows)


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

        first, second = (target, row) if payload.merge_with == "previous" else (row, target)
        origins = list(dict.fromkeys([*source_keys(first), *source_keys(second)]))
        agreed_edited = agreed_was_edited(first) or agreed_was_edited(second)
        for column in ("party_1_text", "party_2_text", "agreed_text", "point_label"):
            left, right = getattr(first, column) or "", getattr(second, column) or ""
            separator = ", " if column == "point_label" else "\n"
            value = separator.join(part for part in (left, right) if part)
            if column == "agreed_text" and left == right:
                value = left
            setattr(target, column, value)
        target.source_clause_keys = origins
        target.source_clause_key = origins[0] if origins else None
        target.agreed_text_edited = agreed_edited
        target.confidence = min(first.confidence, second.confidence)
        target.user_edited = True
        target.flags = sorted({*(target.flags or []), *(row.flags or []), "USER_EDITED"})
        db.delete(row)
        normalize_order([sibling for sibling in siblings if sibling.id != row.id])
        refresh_for_protocol(db, protocol_id)
        db.commit()
        return _serialize_row(target)

    for column in ("point_label", "party_1_text", "party_2_text", "agreed_text"):
        value = getattr(payload, column)
        if value is not None:
            setattr(row, column, value)
            if column == "agreed_text":
                row.agreed_text_edited = True
    row.user_edited = True
    if "USER_EDITED" not in (row.flags or []):
        row.flags = [*list(row.flags or []), "USER_EDITED"]
    refresh_for_protocol(db, protocol_id)
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
    refresh_validation(db, doc, rows)
    data = ProtocolExporter().export(
        payload_rows, drafting.role, counterparty.role, doc.contract_name,
        form=resolve_form(protocol, doc, parties), drafting_party_id=str(drafting.id),
    )
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
    normalize_order(existing)
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
        source_clause_keys=[],
        agreed_text_edited=True,
        confidence=1.0,
        flags=["MANUALLY_ADDED"],
        user_edited=True,
    )
    db.add(new_row)
    refresh_for_protocol(db, protocol_id)
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

    db.delete(row)
    rest = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    normalize_order([rest_row for rest_row in rest if rest_row.id != row_id])
    refresh_for_protocol(db, protocol_id)
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
    return _serialize_protocol(db, protocol, rows)


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
            _serialize_protocol(db, protocol, rows),
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

    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    synchronize_agreed(rows, other.role)
    doc.drafting_party_id = other.id
    if doc.status == DocumentStatus.EXPORTED:
        doc.status = DocumentStatus.BUILT
    refresh_validation(db, doc, rows)
    db.commit()
    return _serialize_protocol(db, protocol, rows)
