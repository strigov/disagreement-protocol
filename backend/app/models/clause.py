import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    clause_key: Mapped[str] = mapped_column(String(64))   # deterministic id like "c_p_0007"
    label: Mapped[str] = mapped_column(String(128))
    level: Mapped[int] = mapped_column(Integer, default=0)
    parent_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text, default="")
    accepted_text: Mapped[str] = mapped_column(Text, default="")
    flags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    confidence: Mapped[float] = mapped_column(default=1.0)
    revisions: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    # Serialized tables attached to this clause: list of
    # {"block_id": str, "has_revisions": bool, "rows": [[cell_text, ...], ...]}.
    # Empty list when the clause has no tables.
    tables_json: Mapped[list[dict]] = mapped_column(JSONB, default=list)
