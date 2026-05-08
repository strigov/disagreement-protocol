import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))


class ProtocolRow(Base):
    __tablename__ = "protocol_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("protocols.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer)
    point_label: Mapped[str] = mapped_column(String(128))
    party_1_text: Mapped[str] = mapped_column(Text, default="")
    party_2_text: Mapped[str] = mapped_column(Text, default="")
    agreed_text: Mapped[str] = mapped_column(Text, default="")
    source_clause_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    flags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
