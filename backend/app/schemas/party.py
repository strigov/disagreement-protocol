from uuid import UUID

from pydantic import BaseModel


class PartyOut(BaseModel):
    id: UUID
    name: str
    role: str
    confidence: float


class PartyUpdateItem(BaseModel):
    id: UUID | None = None
    name: str
    role: str


class PartiesUpdateIn(BaseModel):
    parties: list[PartyUpdateItem]
    drafting_party_id: UUID | None = None
