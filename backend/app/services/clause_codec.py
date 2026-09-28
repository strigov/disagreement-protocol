"""Lossless clause persistence, including old databases without paragraph metadata."""
from dataclasses import asdict

from app.models.clause import Clause as ClauseModel
from app.processing.types import (
    Clause, EnrichedParagraph, RawTable, RawTableCell, RawTableRow, RevisionRecord,
)
from app.services.protocol_generator import render_clause


def restore_revisions(data) -> tuple[RevisionRecord, ...]:
    return tuple(
        RevisionRecord(r.get("type", ""), r.get("text", ""), r.get("author", ""))
        for r in (data or [])
    )


def restore_clause(model: ClauseModel, block_order: dict[str, int] | None = None) -> Clause:
    block_order = block_order or {}
    clause = Clause(model.clause_key, model.label, model.level, model.parent_key)
    clause.flags = set(model.flags or [])
    paragraphs = model.paragraphs_json
    if paragraphs is None:
        paragraphs = [{
            "block_id": model.clause_key, "original_text": model.original_text,
            "accepted_text": model.accepted_text, "revisions": model.revisions,
        }]
    for p in paragraphs:
        clause.paragraphs.append(EnrichedParagraph(
            block_id=p.get("block_id", ""),
            block_index=p.get("block_index", block_order.get(p.get("block_id"))),
            text_runs=p.get("text_runs", p.get("accepted_text", "")),
            num_id=p.get("num_id"), ilvl=p.get("ilvl"),
            original_text=p.get("original_text", ""), accepted_text=p.get("accepted_text", ""),
            revisions=restore_revisions(p.get("revisions")),
            rendered_number=p.get("rendered_number"),
            numbering_confidence=p.get("numbering_confidence", model.confidence or 0.0),
            numbering_level=p.get("numbering_level"),
        ))
    for table in model.tables_json or []:
        metadata = table.get("row_metadata", [])
        rows = []
        for i, cells in enumerate(table.get("rows", [])):
            row_info = metadata[i] if i < len(metadata) else {}
            restored_cells = []
            for cell in cells:
                if isinstance(cell, str):
                    cell = {"original_text": cell, "accepted_text": cell}
                restored_cells.append(RawTableCell(
                    paragraphs=(),
                    original_text=cell.get("original_text", ""),
                    accepted_text=cell.get("accepted_text", ""),
                    revisions=restore_revisions(cell.get("revisions")),
                    exists_in_original=cell.get("exists_in_original", True),
                    exists_in_accepted=cell.get("exists_in_accepted", True),
                ))
            rows.append(RawTableRow(
                cells=tuple(restored_cells),
                exists_in_original=row_info.get("exists_in_original", True),
                exists_in_accepted=row_info.get("exists_in_accepted", True),
                revisions=restore_revisions(row_info.get("revisions")),
            ))
        clause.tables.append(RawTable(
            block_id=table["block_id"],
            block_index=table.get("block_index", block_order.get(table["block_id"])),
            rows=tuple(rows), has_revisions=bool(table.get("has_revisions", False)),
        ))
    if clause.tables and clause.paragraphs and any(
        block.block_index is None for block in [*clause.paragraphs, *clause.tables]
    ):
        clause.flags.add("SOURCE_ORDER_UNAVAILABLE")
    return clause


def serialize_clause(clause: Clause, document_id, sort_order: int) -> ClauseModel:
    confidences = [p.numbering_confidence for p in clause.paragraphs]
    tables = []
    for table in clause.tables:
        rows = []
        for row in table.rows:
            cells = []
            for cell in row.cells:
                data = {
                    "original_text": cell.text("original"),
                    "accepted_text": cell.text("accepted"),
                    "revisions": [asdict(r) for r in cell.revisions],
                }
                if not cell.exists_in_original or not cell.exists_in_accepted:
                    data.update(exists_in_original=cell.exists_in_original,
                                exists_in_accepted=cell.exists_in_accepted)
                cells.append(data)
            rows.append(cells)
        tables.append({
            "block_id": table.block_id, "block_index": table.block_index,
            "has_revisions": table.has_revisions, "rows": rows,
            "row_metadata": [{
                "exists_in_original": r.exists_in_original,
                "exists_in_accepted": r.exists_in_accepted,
                "revisions": [asdict(rev) for rev in r.revisions],
            } for r in table.rows],
        })
    return ClauseModel(
        document_id=document_id, sort_order=sort_order, clause_key=clause.clause_key,
        label=clause.label, level=clause.level, parent_key=clause.parent_key,
        original_text=render_clause(clause, "original"),
        accepted_text=render_clause(clause, "accepted"),
        flags=sorted(clause.flags), confidence=sum(confidences) / len(confidences) if confidences else 0.0,
        revisions=[asdict(r) for p in clause.paragraphs for r in p.revisions],
        paragraphs_json=[{**asdict(p), "revisions": [asdict(r) for r in p.revisions]}
                         for p in clause.paragraphs], tables_json=tables,
    )
