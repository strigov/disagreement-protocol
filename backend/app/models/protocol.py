import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Protocol(Base):
    __tablename__ = "protocols"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id", ondelete="CASCADE"))


class ProtocolRow(Base):
    __tablename__ = "protocol_rows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("protocols.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer)
    point_label: Mapped[str] = mapped_column(String(128))
    party_1_text: Mapped[str] = mapped_column(Text, default="")
    # NB: an invariant shared by builder/exporter/swap-parties: party_2_text is
    # ALWAYS the proposing (drafting) party's edition, party_1_text — the
    # counterparty's. Swapping parties relabels headers and agreed_text only.
    party_2_text: Mapped[str] = mapped_column(Text, default="")
    agreed_text: Mapped[str] = mapped_column(Text, default="")
    source_clause_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
