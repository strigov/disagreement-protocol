from __future__ import annotations

from dataclasses import dataclass, field

from app.processing.types import Clause, ResolverDiagnostic
from app.services.protocol_generator import BuiltRow


@dataclass
class ValidationReport:
    textual_revisions_total: int
    format_only_revisions: int
    covered_revisions: int
    numbering_confidence_mean: float
    warnings: list[dict] = field(default_factory=list)


class ValidationEngine:
    def validate(
        self,
        protocol_rows: list[BuiltRow],
        all_clauses: list[Clause],
        resolver_diagnostics: list[ResolverDiagnostic],
    ) -> ValidationReport:
        """Build a ValidationReport for the protocol.

        Inputs:
        - `protocol_rows`: the rows produced by ProtocolRowBuilder for the
          current build (used for emptiness check and TABLE_CELL_CHANGE
          warnings).
        - `all_clauses`: the full list of clauses in the document (NOT just
          the `changed_clauses` subset). Counting revisions and computing
          numbering confidence over all clauses ensures format-only
          revisions on otherwise-unchanged clauses are still tallied - a
          clause whose only revision is FORMAT_ONLY does not enter
          `changed_clauses`, so passing only the changed subset would
          silently drop those revisions from `format_only_revisions`.
        - `resolver_diagnostics`: aggregated diagnostics from the revision
          and numbering resolvers. Diagnostics are routed by their `code`,
          not by their `component`, because mapping by component alone
          produces false positives (e.g. a benign FORMAT_ONLY_MISMATCH from
          the revision resolver would otherwise surface as a
          REVISION_MAPPING_MISMATCH warning). The mapping is:
            - code="UNKNOWN_NUMID"        -> NUMBERING_MAPPING_MISMATCH
            - code="LOW_CONFIDENCE"       -> LOW_NUMBERING_CONFIDENCE
            - code="FORMAT_ONLY_MISMATCH" -> suppressed (expected behaviour)
            - code="MAPPING_MISMATCH"     -> REVISION_MAPPING_MISMATCH if
                                            component=="revision",
                                            NUMBERING_MAPPING_MISMATCH if
                                            component=="numbering"
            - any other code              -> passed through verbatim as
                                            kind=code, scope="session"
        """
        textual = 0
        covered = 0
        format_only = 0
        confidences: list[float] = []
        warnings: list[dict] = []
        covered_keys = {
            key
            for row in protocol_rows
            if (row.party_1_text or "").strip() or (row.party_2_text or "").strip()
            for key in (row.source_clause_keys or [row.source_clause_key])
            if key
        }

        for clause in all_clauses:
            before = textual
            for paragraph in clause.paragraphs:
                for revision in paragraph.revisions:
                    if revision.type in ("INS", "DEL"):
                        textual += 1
                    elif revision.type == "FORMAT_ONLY":
                        format_only += 1
                if paragraph.numbering_confidence is not None:
                    confidences.append(paragraph.numbering_confidence)
            for table in clause.tables:
                for row in table.rows:
                    for revision in row.revisions:
                        if revision.type in ("INS", "DEL"):
                            textual += 1
                        elif revision.type == "FORMAT_ONLY":
                            format_only += 1
                    for cell in row.cells:
                        for revision in cell.revisions:
                            if revision.type in ("INS", "DEL"):
                                textual += 1
                            elif revision.type == "FORMAT_ONLY":
                                format_only += 1

            if clause.clause_key in covered_keys:
                covered += textual - before
            elif textual > before:
                warnings.append({
                    "kind": "UNCOVERED_REVISIONS", "scope": "clause", "severity": "warning",
                    "clause_key": clause.clause_key,
                    "message": f"Правки пункта {clause.label} не представлены в протоколе ({textual - before})",
                })
            if "SOURCE_ORDER_UNAVAILABLE" in clause.flags:
                warnings.append({
                    "kind": "SOURCE_ORDER_UNAVAILABLE", "scope": "clause", "severity": "warning",
                    "clause_key": clause.clause_key,
                    "message": f"Порядок текста и таблиц пункта {clause.label} не сохранён в старой версии. "
                               "Проверьте по исходному документу.",
                })

            if "MULTI_PARAGRAPH" in clause.flags:
                warnings.append(
                    {
                        "kind": "MULTI_PARAGRAPH",
                        "scope": "clause",
                        "clause_key": clause.clause_key,
                        "message": f"Пункт {clause.label} состоит из нескольких параграфов",
                    },
                )
            if "LOW_NUMBERING_CONFIDENCE" in clause.flags:
                warnings.append(
                    {
                        "kind": "LOW_NUMBERING_CONFIDENCE",
                        "scope": "clause",
                        "clause_key": clause.clause_key,
                        "message": f"Низкая уверенность нумерации в пункте {clause.label}",
                    },
                )

        mean = sum(confidences) / len(confidences) if confidences else 0.0
        if confidences and mean < 0.6:
            warnings.append(
                {
                    "kind": "LOW_NUMBERING_CONFIDENCE_OVERALL",
                    "scope": "session",
                    "message": "Нумерация распознана с низкой уверенностью",
                },
            )
        if not confidences:
            warnings.append(
                {
                    "kind": "LOW_NUMBERING_CONFIDENCE_OVERALL",
                    "scope": "session",
                    "message": "Нумерация не распознана",
                },
            )
        if not protocol_rows:
            warnings.append(
                {
                    "kind": "EMPTY_PROTOCOL",
                    "scope": "session",
                    "severity": "warning" if textual else "info",
                    "message": (
                        "Протокол пуст, хотя в исходном документе есть правки"
                        if textual else "В документе не найдено текстовых правок"
                    ),
                },
            )

        for diagnostic in resolver_diagnostics:
            if diagnostic.code == "FORMAT_ONLY_MISMATCH":
                continue
            if diagnostic.code == "UNKNOWN_NUMID":
                kind = "NUMBERING_MAPPING_MISMATCH"
            elif diagnostic.code == "LOW_CONFIDENCE":
                kind = "LOW_NUMBERING_CONFIDENCE"
            elif diagnostic.code == "MAPPING_MISMATCH":
                kind = (
                    "NUMBERING_MAPPING_MISMATCH"
                    if diagnostic.component == "numbering"
                    else "REVISION_MAPPING_MISMATCH"
                )
            else:
                kind = diagnostic.code
            warnings.append(
                {
                    "kind": kind,
                    "scope": "session",
                    "severity": diagnostic.level,
                    "component": diagnostic.component,
                    "code": diagnostic.code,
                    "block_id": diagnostic.block_id,
                    "message": diagnostic.message,
                },
            )

        for row in protocol_rows:
            if "TABLE_CELL_CHANGE" in (row.flags or []):
                warnings.append(
                    {
                        "kind": "TABLE_CELL_CHANGE",
                        "scope": "row",
                        "severity": "warning",
                        "row_id": row.row_id,
                        "point_label": row.point_label,
                        "source_clause_key": row.source_clause_key,
                        "message": f"Таблица в пункте {row.point_label} требует проверки",
                    },
                )

        return ValidationReport(
            textual_revisions_total=textual,
            format_only_revisions=format_only,
            covered_revisions=covered,
            numbering_confidence_mean=mean,
            warnings=warnings,
        )
