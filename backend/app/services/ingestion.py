from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from app.processing.docx_package import DocxPackage, MAX_FILE_BYTES, PackageError
from app.processing.changed_clause_detector import ChangedClauseDetector
from app.processing.clause_segmenter import ClauseSegmenter
from app.processing.numbering_resolver import NumberingResolver
from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import (
    EnrichedParagraph,
    RawParagraph,
    RawTable,
    RawTableCell,
    RawTableRow,
)
from app.services.party_extractor import PartyExtractor

MAX_BYTES = MAX_FILE_BYTES


class IngestError(Exception):
    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


def validate_upload(filename: str, data: bytes) -> None:
    if not filename.lower().endswith(".docx"):
        raise IngestError(400, "Поддерживаются только файлы .docx без макросов")
    if len(data) > MAX_BYTES:
        raise IngestError(413, "Размер файла превышает 25 МБ")
    try:
        with DocxPackage(data):
            pass
    except PackageError as exc:
        raise IngestError(exc.http_status, str(exc)) from exc


def derive_contract_name(filename: str) -> str | None:
    name = filename
    if name.lower().endswith(".docx"):
        name = name[:-5]
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name or None


def _resolve_table(table: RawTable, revision_map: dict, package: DocxPackage) -> RawTable:
    rows: list[RawTableRow] = []
    for row in package.checked(table.rows):
        cells: list[RawTableCell] = []
        for cell in package.checked(row.cells):
            original_parts: list[str] = []
            accepted_parts: list[str] = []
            revisions = list(cell.revisions)
            for paragraph in package.checked(cell.paragraphs):
                revision_data = revision_map.get(paragraph.block_id)
                if revision_data is None:
                    original_parts.append(paragraph.text())
                    accepted_parts.append(paragraph.text())
                    continue
                original_parts.append(revision_data.original_text)
                accepted_parts.append(revision_data.accepted_text)
                revisions.extend(revision_data.revisions)
            cells.append(
                replace(
                    cell,
                    original_text=" ".join(original_parts).strip(),
                    accepted_text=" ".join(accepted_parts).strip(),
                    revisions=tuple(revisions),
                ),
            )
        rows.append(replace(row, cells=tuple(cells)))
    return replace(table, rows=tuple(rows))


def _iter_clause_revisions(clauses):
    for clause in clauses:
        for paragraph in clause.paragraphs:
            yield from paragraph.revisions
        for table in clause.tables:
            for row in table.rows:
                yield from row.revisions
                for cell in row.cells:
                    yield from cell.revisions


def run_pipeline(data: bytes) -> dict[str, Any]:
    with DocxPackage(data) as package:
        return _run_pipeline(package)


def _run_pipeline(data: DocxPackage) -> dict[str, Any]:
    parser = OOXMLParser()
    raw = parser.parse(data)
    revisions, revision_diags = RevisionResolver().resolve(data, raw)
    numbering, numbering_diags = NumberingResolver().resolve(data, raw, revisions)

    segmenter_blocks: list[EnrichedParagraph | RawTable] = []
    for block in data.checked(raw.blocks):
        if isinstance(block, RawParagraph):
            rd = revisions.get(block.block_id)
            nd = numbering.get(block.block_id)
            enriched = EnrichedParagraph(
                block_id=block.block_id,
                text_runs=block.text(),
                num_id=block.num_id,
                ilvl=block.ilvl,
                original_text=rd.original_text if rd else block.text(),
                accepted_text=rd.accepted_text if rd else block.text(),
                revisions=rd.revisions if rd else (),
                rendered_number=nd.rendered_number if nd else None,
                numbering_confidence=nd.confidence if nd else 0.0,
                numbering_level=nd.numbering_level if nd else None,
                block_index=block.block_index,
            )
            segmenter_blocks.append(enriched)
        elif isinstance(block, RawTable):
            segmenter_blocks.append(_resolve_table(block, revisions, data))

    clauses = ClauseSegmenter().segment(segmenter_blocks, check_budget=data.check_budget)
    changed = ChangedClauseDetector().detect(clauses, check_budget=data.check_budget)
    preamble_text = ""
    for clause in data.checked(clauses):
        if clause.label == "Преамбула":
            preamble_text = "\n".join(paragraph.accepted_text for paragraph in clause.paragraphs)
            break
    if not preamble_text and clauses:
        preamble_text = "\n".join(paragraph.accepted_text for paragraph in clauses[0].paragraphs)

    parties = PartyExtractor().extract(preamble_text, check_budget=data.check_budget)
    all_revisions = list(data.checked(_iter_clause_revisions(clauses)))
    diagnostics = [
        {
            "level": diagnostic.level,
            "component": diagnostic.component,
            "code": diagnostic.code,
            "message": diagnostic.message,
            "block_id": diagnostic.block_id,
        }
        for diagnostic in (*revision_diags, *numbering_diags)
    ]
    paragraph_count = sum(len(clause.paragraphs) for clause in clauses)
    result = {
        "clauses": clauses,
        "changed_clauses": changed,
        "parties": parties,
        "preflight_metrics": {
            "revisions_total": sum(
                1 for revision in all_revisions if revision.type in ("INS", "DEL")
            ),
            "format_only_count": sum(1 for revision in all_revisions if revision.type == "FORMAT_ONLY"),
            "paragraphs_with_numbering": sum(
                1
                for clause in clauses
                for paragraph in clause.paragraphs
                if paragraph.rendered_number
            ),
            "numbering_confidence_mean": (
                sum(
                    paragraph.numbering_confidence
                    for clause in clauses
                    for paragraph in clause.paragraphs
                )
                / max(1, paragraph_count)
            ),
        },
        "preflight_diagnostics": diagnostics,
    }
    data.check_budget()
    return result
