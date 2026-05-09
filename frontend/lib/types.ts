export type UUID = string;

export interface Party {
  id: UUID;
  name: string;
  role: string;
  confidence: number;
}

export interface PreflightMetrics {
  revisions_total: number;
  format_only_count: number;
  paragraphs_with_numbering: number;
  numbering_confidence_mean: number;
}

export interface ValidationWarning {
  kind: string;
  scope: string;
  clause_key?: string | null;
  row_id?: string | null;
  message: string;
  severity?: string;
}

export interface ValidationReport {
  textual_revisions_total: number;
  format_only_revisions: number;
  covered_revisions: number;
  numbering_confidence_mean: number;
  warnings: ValidationWarning[];
}

export interface PreflightDiagnostic {
  level: "warning" | "error";
  component: string;
  code: string;
  message: string;
  block_id: string | null;
}

export interface AnalysisOut {
  id: UUID;
  status: string;
  contract_name: string | null;
  preflight_metrics: PreflightMetrics | null;
  preflight_diagnostics: PreflightDiagnostic[];
  parties: Party[];
  validation_report: ValidationReport | null;
  drafting_party_id: UUID | null;
}

export interface ProtocolRow {
  id: UUID;
  sort_order: number;
  point_label: string;
  party_1_text: string;
  party_2_text: string;
  agreed_text: string;
  source_clause_key: string | null;
  confidence: number;
  flags: string[];
  user_edited: boolean;
}

export interface Protocol {
  id: UUID;
  document_id: UUID;
  rows: ProtocolRow[];
}
