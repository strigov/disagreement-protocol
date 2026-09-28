import type { ProtocolRow, ValidationWarning } from "./types";

export const rowFingerprint = (row: ProtocolRow, context = "") => JSON.stringify([
  context, row.point_label, row.party_1_text, row.party_2_text, row.agreed_text,
  row.source_clause_key, row.flags, row.confidence,
]);

export const warningsForRow = (row: ProtocolRow, warnings: ValidationWarning[]) => warnings.filter(
  (warning) => warning.row_id === row.id || (!!row.source_clause_key && warning.clause_key === row.source_clause_key),
);

export const needsAttention = (row: ProtocolRow, warnings: ValidationWarning[] = []) =>
  row.confidence < 0.85 || row.flags.includes("manual_review") || row.flags.includes("LOW_NUMBERING_CONFIDENCE") || warningsForRow(row, warnings).length > 0;
