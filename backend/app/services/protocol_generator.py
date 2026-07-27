from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.processing.types import Clause


@dataclass
class BuildContext:
    drafting_party_role: str
    counterparty_role: str


@dataclass
class BuiltRow:
    point_label: str
    party_1_text: str
    party_2_text: str
    agreed_text: str
    source_clause_key: str | None
    confidence: float
    flags: list[str] = field(default_factory=list)
    row_id: str | None = None


_GENITIVE_RULES = {
    "Арендатор": "Арендатора",
    "Арендодатель": "Арендодателя",
    "Заказчик": "Заказчика",
    "Исполнитель": "Исполнителя",
    "Поставщик": "Поставщика",
    "Покупатель": "Покупателя",
    "Подрядчик": "Подрядчика",
    "Продавец": "Продавца",
    "Лицензиар": "Лицензиара",
    "Лицензиат": "Лицензиата",
    "Заёмщик": "Заёмщика",
    "Займодавец": "Займодавца",
    "Агент": "Агента",
    "Принципал": "Принципала",
    "Поручитель": "Поручителя",
    "Перевозчик": "Перевозчика",
}


def edition_label(role: str, empty_fallback: str) -> str:
    normalized_role = (role or "").strip()
    if not normalized_role:
        return f"Редакция {empty_fallback}"
    if normalized_role in _GENITIVE_RULES:
        return f"Редакция {_GENITIVE_RULES[normalized_role]}"
    return f"Редакция стороны «{normalized_role}»"


def agreed_text_for_party(role: str) -> str:
    return edition_label(role, "Стороны 2")


class ProtocolRowBuilder:
    def build(self, clauses: list[Clause], ctx: BuildContext) -> list[BuiltRow]:
        rows: list[BuiltRow] = []
        new_clause_counter = 0
        agreed = agreed_text_for_party(ctx.drafting_party_role)

        for clause in clauses:
            if "STANDALONE_TABLE" in clause.flags:
                rows.append(self._standalone_table_row(clause, agreed))
                continue

            original = "\n".join(paragraph.original_text for paragraph in clause.paragraphs)
            accepted = "\n".join(paragraph.accepted_text for paragraph in clause.paragraphs)
            flags = set(clause.flags)

            if clause.tables:
                if any(table.has_revisions for table in clause.tables):
                    flags.add("TABLE_CELL_CHANGE")
                original_table_text = self._render_tables(clause, "original")
                accepted_table_text = self._render_tables(clause, "accepted")
                if original_table_text:
                    original = f"{original}\n{original_table_text}" if original else original_table_text
                if accepted_table_text:
                    accepted = f"{accepted}\n{accepted_table_text}" if accepted else accepted_table_text

            if "NEW_CLAUSE" in clause.flags:
                new_clause_counter += 1
                rows.append(
                    BuiltRow(
                        point_label=f"Новый пункт {new_clause_counter}",
                        party_1_text="—",
                        party_2_text=accepted,
                        agreed_text=agreed,
                        source_clause_key=clause.clause_key,
                        confidence=self._confidence(clause),
                        flags=sorted(flags),
                    ),
                )
                continue

            if "DELETED_CLAUSE" in clause.flags:
                rows.append(
                    BuiltRow(
                        point_label=clause.label,
                        party_1_text=original,
                        party_2_text=f"Исключить пункт {clause.label}",
                        agreed_text=agreed,
                        source_clause_key=clause.clause_key,
                        confidence=self._confidence(clause),
                        flags=sorted(flags),
                    ),
                )
                continue

            rows.append(
                BuiltRow(
                    point_label=clause.label,
                    party_1_text=original,
                    party_2_text=accepted,
                    agreed_text=agreed,
                    source_clause_key=clause.clause_key,
                    confidence=self._confidence(clause),
                    flags=sorted(flags),
                ),
            )

        return rows

    def _standalone_table_row(self, clause: Clause, agreed: str) -> BuiltRow:
        original_table_text = self._render_tables(clause, "original")
        accepted_table_text = self._render_tables(clause, "accepted")
        flags = {*clause.flags, "manual_review"}
        if any(table.has_revisions for table in clause.tables):
            flags.add("TABLE_CELL_CHANGE")

        return BuiltRow(
            point_label="Таблица",
            party_1_text=original_table_text,
            party_2_text=accepted_table_text,
            agreed_text=agreed,
            source_clause_key=clause.clause_key,
            confidence=0.5,
            flags=sorted(flags),
        )

    def _render_tables(self, clause: Clause, version: Literal["original", "accepted"]) -> str:
        parts: list[str] = []
        for table in clause.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text(version) for cell in row.cells))
        return "\n".join(parts)

    def _confidence(self, clause: Clause) -> float:
        if "MULTI_PARAGRAPH" in clause.flags:
            return 0.7
        if "LOW_NUMBERING_CONFIDENCE" in clause.flags:
            return 0.6
        return 0.95
