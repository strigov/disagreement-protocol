import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum as SAEnum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DocumentStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(512))
    storage_key: Mapped[str] = mapped_column(String(512))
    contract_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus, name="document_status", values_callable=lambda cls: [e.value for e in cls]),
        default=DocumentStatus.UPLOADED,
    )
    drafting_party_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    preflight_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Free-form pipeline metadata. Currently stores
    # {"preflight_diagnostics": [{level, component, code, message, block_id}, ...]}.
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
