from pydantic import BaseModel


class WarningOut(BaseModel):
    kind: str
    scope: str
    clause_key: str | None = None
    row_id: str | None = None
    message: str
    severity: str = "warning"


class ValidationReportOut(BaseModel):
    textual_revisions_total: int
    format_only_revisions: int
    covered_revisions: int
    numbering_confidence_mean: float
    warnings: list[WarningOut]
