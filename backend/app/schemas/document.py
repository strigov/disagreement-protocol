from uuid import UUID

from pydantic import BaseModel

from app.schemas.party import PartyOut
from app.schemas.validation import ValidationReportOut


class DocumentCreated(BaseModel):
    id: UUID
    status: str


class PreflightMetrics(BaseModel):
    revisions_total: int
    format_only_count: int
    paragraphs_with_numbering: int
    numbering_confidence_mean: float


class PreflightDiagnostic(BaseModel):
    level: str
    component: str
    code: str = "MAPPING_MISMATCH"
    message: str
    block_id: str | None = None


class AnalysisOut(BaseModel):
    id: UUID
    status: str
    contract_name: str | None
    preflight_metrics: PreflightMetrics | None
    preflight_diagnostics: list[PreflightDiagnostic] = []
    parties: list[PartyOut]
    validation_report: ValidationReportOut | None = None
    drafting_party_id: UUID | None
