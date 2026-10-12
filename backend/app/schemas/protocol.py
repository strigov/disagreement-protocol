from uuid import UUID

from pydantic import BaseModel

from app.schemas.protocol_form import ProtocolForm
from app.schemas.export_style import ChangeHighlighting


class ProtocolRowOut(BaseModel):
    id: UUID
    sort_order: int
    point_label: str
    party_1_text: str
    party_2_text: str
    agreed_text: str
    source_clause_key: str | None
    confidence: float
    flags: list[str]
    user_edited: bool


class ProtocolOut(BaseModel):
    id: UUID
    document_id: UUID
    rows: list[ProtocolRowOut]
    form: ProtocolForm


class ProtocolRowPatch(BaseModel):
    point_label: str | None = None
    party_1_text: str | None = None
    party_2_text: str | None = None
    agreed_text: str | None = None
    # Optional row-merge directive: when set to "previous" or "next",
    # the row's text columns are appended to the neighbouring row (joined
    # by newline) and the current row is deleted in the same transaction.
    merge_with: str | None = None


class ProtocolRowCreate(BaseModel):
    sort_order: int | None = None  # None = append to the end


class ExportRequest(BaseModel):
    filename: str
    highlighting: ChangeHighlighting | None = None
