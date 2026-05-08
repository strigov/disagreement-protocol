from __future__ import annotations

from app.processing.types import Clause


class ChangedClauseDetector:
    def detect(self, clauses: list[Clause]) -> list[Clause]:
        out: list[Clause] = []
        for clause in clauses:
            textual = [
                revision
                for paragraph in clause.paragraphs
                for revision in paragraph.revisions
                if revision.type in ("INS", "DEL")
            ]
            has_table_revisions = any(table.has_revisions for table in clause.tables)
            is_standalone_table = "STANDALONE_TABLE" in clause.flags
            if not (textual or has_table_revisions or is_standalone_table):
                continue

            if textual and clause.paragraphs:
                textual_types = [
                    revision.type
                    for paragraph in clause.paragraphs
                    for revision in paragraph.revisions
                    if revision.type in ("INS", "DEL")
                ]
                if all(paragraph.original_text.strip() == "" for paragraph in clause.paragraphs) and all(
                    revision_type == "INS" for revision_type in textual_types
                ):
                    clause.flags.add("NEW_CLAUSE")
                if all(paragraph.accepted_text.strip() == "" for paragraph in clause.paragraphs) and all(
                    revision_type == "DEL" for revision_type in textual_types
                ):
                    clause.flags.add("DELETED_CLAUSE")

            out.append(clause)
        return out
