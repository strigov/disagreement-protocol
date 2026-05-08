"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("contract_name", sa.String(512), nullable=True),
        sa.Column("status", sa.Enum("uploaded", "parsing", "parsed", "parties_confirmed", "built", "exported", "failed", name="document_status"), nullable=False),
        sa.Column("drafting_party_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preflight_metrics", postgresql.JSONB, nullable=True),
        sa.Column("validation_report", postgresql.JSONB, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "parties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("role", sa.String(256), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
    )
    op.create_table(
        "clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clause_key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("parent_key", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("original_text", sa.Text, nullable=False, server_default=""),
        sa.Column("accepted_text", sa.Text, nullable=False, server_default=""),
        sa.Column("flags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("revisions", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tables_json", postgresql.JSONB, nullable=False, server_default="[]"),
    )
    op.create_table(
        "protocols",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_table(
        "protocol_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("protocol_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("protocols.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False),
        sa.Column("point_label", sa.String(128), nullable=False),
        sa.Column("party_1_text", sa.Text, nullable=False, server_default=""),
        sa.Column("party_2_text", sa.Text, nullable=False, server_default=""),
        sa.Column("agreed_text", sa.Text, nullable=False, server_default=""),
        sa.Column("source_clause_key", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("flags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("user_edited", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_table("protocol_rows")
    op.drop_table("protocols")
    op.drop_table("clauses")
    op.drop_table("parties")
    op.drop_table("documents")
    op.execute("DROP TYPE document_status")
