from __future__ import annotations

import re
from typing import Sequence, Union

from app.processing.types import Clause, EnrichedParagraph, RawTable

Block = Union[EnrichedParagraph, RawTable]

_REQUISITES_RE = re.compile(
    r"^(?:"
    r"реквизиты\s+сторон"
    r"|подписи\s+сторон"
    r"|подписи\s+и\s+реквизиты(?:\s+сторон)?"
    r"|адреса\s+и\s+реквизиты(?:\s+сторон)?"
    r"|реквизиты"
    r")\s*$",
    re.IGNORECASE,
)
_ANNEX_RE = re.compile(r"^\s*приложение\s*[№#]?\s*\d+", re.IGNORECASE)


class ClauseSegmenter:
    def segment(self, blocks: Sequence[Block]) -> list[Clause]:
        clauses: list[Clause] = []
        stack: list[Clause] = []
        preamble: Clause | None = None
        current_requisites_clause: Clause | None = None
        current_annex_clause: Clause | None = None
        current_annex_label: str | None = None

        last_requisites_idx: int | None = None
        all_paras = [b for b in blocks if isinstance(b, EnrichedParagraph)]
        window = all_paras[-30:] if len(all_paras) >= 30 else all_paras
        for p in window:
            if _REQUISITES_RE.match(p.text_runs.strip()):
                last_requisites_idx = blocks.index(p)
                break

        for current_block_index, block in enumerate(blocks):
            if current_requisites_clause is not None:
                if isinstance(block, RawTable):
                    current_requisites_clause.tables.append(block)
                else:
                    current_requisites_clause.paragraphs.append(block)
                continue

            if isinstance(block, RawTable):
                if stack:
                    stack[-1].tables.append(block)
                elif current_annex_clause is not None:
                    current_annex_clause.tables.append(block)
                elif preamble is not None:
                    preamble.tables.append(block)
                else:
                    table_clause = Clause(
                        clause_key=f"c_{block.block_id}",
                        label="Таблица",
                        level=0,
                        parent_key=None,
                    )
                    table_clause.tables.append(block)
                    table_clause.flags.add("STANDALONE_TABLE")
                    clauses.append(table_clause)
                continue

            paragraph = block
            if current_block_index == last_requisites_idx:
                stack.clear()
                current_annex_clause = None
                current_annex_label = None
                current_requisites_clause = Clause(
                    clause_key=f"c_{paragraph.block_id}",
                    label="Реквизиты сторон",
                    level=0,
                    parent_key=None,
                )
                current_requisites_clause.paragraphs.append(paragraph)
                clauses.append(current_requisites_clause)
                continue

            annex_match = _ANNEX_RE.match(paragraph.text_runs.strip())
            if annex_match:
                stack.clear()
                current_annex_label = paragraph.text_runs.strip()
                current_annex_clause = Clause(
                    clause_key=f"c_{paragraph.block_id}",
                    label=current_annex_label,
                    level=0,
                    parent_key=None,
                )
                current_annex_clause.paragraphs.append(paragraph)
                clauses.append(current_annex_clause)
                continue

            level = self._level_of(paragraph)
            if level is None:
                if stack:
                    stack[-1].paragraphs.append(paragraph)
                    if len(stack[-1].paragraphs) > 1:
                        stack[-1].flags.add("MULTI_PARAGRAPH")
                elif current_annex_clause is not None:
                    current_annex_clause.paragraphs.append(paragraph)
                    if len(current_annex_clause.paragraphs) > 1:
                        current_annex_clause.flags.add("MULTI_PARAGRAPH")
                else:
                    if preamble is None:
                        preamble = Clause(
                            clause_key=f"c_{paragraph.block_id}",
                            label="Преамбула",
                            level=0,
                            parent_key=None,
                        )
                        clauses.append(preamble)
                    preamble.paragraphs.append(paragraph)
                continue

            while stack and stack[-1].level >= level:
                stack.pop()

            if stack:
                parent_key = stack[-1].clause_key
            elif current_annex_clause is not None and current_annex_label is not None:
                parent_key = current_annex_clause.clause_key
            else:
                parent_key = None

            base_label = paragraph.rendered_number or paragraph.text_runs[:32]
            if current_annex_label is not None and paragraph.rendered_number:
                num = paragraph.rendered_number.rstrip(".")
                full_label = f"{current_annex_label}, п. {num}"
            else:
                full_label = base_label

            new_clause = Clause(
                clause_key=f"c_{paragraph.block_id}",
                label=full_label,
                level=level,
                parent_key=parent_key,
            )
            new_clause.paragraphs.append(paragraph)
            clauses.append(new_clause)
            stack.append(new_clause)

        for clause in clauses:
            if len(clause.paragraphs) > 1:
                clause.flags.add("MULTI_PARAGRAPH")
        return clauses

    def _level_of(self, paragraph: EnrichedParagraph) -> int | None:
        if paragraph.num_id is not None and paragraph.ilvl is not None:
            return paragraph.ilvl
        if paragraph.rendered_number:
            return len(paragraph.rendered_number.rstrip(".").split(".")) - 1
        return None
