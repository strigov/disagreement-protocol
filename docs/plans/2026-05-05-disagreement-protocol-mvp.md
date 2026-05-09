---
slug: disagreement-protocol-mvp
created: 2026-05-05
status: in-progress
phases:
  - id: Ф0
    scope: "Project bootstrap"
    status: done
  - id: Ф1
    scope: "OOXMLParser"
    status: done
  - id: Ф2
    scope: "RevisionResolver"
    status: done
  - id: Ф3
    scope: "NumberingResolver"
    status: done
  - id: Ф4
    scope: "ClauseSegmenter"
    status: done
  - id: Ф5
    scope: "ChangedClauseDetector"
    status: done
  - id: Ф6
    scope: "PartyExtractor"
    status: done
  - id: Ф7
    scope: "ProtocolRowBuilder"
    status: done
  - id: Ф8
    scope: "ValidationEngine"
    status: done
  - id: Ф9
    scope: "FastAPI app + Celery wiring + storage"
    status: done
  - id: Ф10
    scope: "Document upload + Celery pipeline task"
    status: done
  - id: Ф11
    scope: "Analysis endpoint + party confirmation"
    status: done
  - id: Ф12
    scope: "Protocol generation + row edit endpoints"
    status: done
  - id: Ф13
    scope: "DOCX export + download endpoint"
    status: done
  - id: Ф14
    scope: "Frontend bootstrap + API client"
    status: done
  - id: Ф15
    scope: "Upload screen"
    status: done
  - id: Ф16
    scope: "Preflight + Parties screens"
    status: done
  - id: Ф17
    scope: "Protocol table screen"
    status: done
  - id: Ф18
    scope: "Export screen"
    status: done
  - id: Ф19
    scope: "Fixtures + end-to-end integration test"
    status: in-progress
---

# Disagreement Protocol MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use dev-orchestrator (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working app that ingests a `.docx` with Word Track Changes and produces a 4-column "Протокол разногласий" DOCX, with an editable web table in between.

**Architecture:** A Python 3.12 FastAPI backend runs a deterministic OOXML pipeline (parser → revisions → numbering → segmenter → changed-clause detector → party extractor → row builder → validator → exporter), persists state in PostgreSQL with documents/files in S3-compatible MinIO, dispatches the pipeline through Celery on Redis, and is consumed by a small Next.js/TypeScript UI that walks the user through five linear screens.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, PostgreSQL 16, Redis 7, Celery 5, lxml, python-docx, docx-revisions, docx2python, rapidfuzz, diff-match-patch, natasha, docxtpl, Next.js 14, TypeScript 5, Tailwind CSS, shadcn/ui, TanStack Table v8, TanStack Query v5. Local dev via Docker Compose (postgres + redis + minio). Tests via pytest + httpx + Playwright (smoke).

---

## Repository layout target

```
disagreement-protocol/
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── documents.py
│   │   │   ├── protocols.py
│   │   │   └── files.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── document.py
│   │   │   ├── party.py
│   │   │   ├── clause.py
│   │   │   ├── protocol.py
│   │   │   └── enums.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── document.py
│   │   │   ├── party.py
│   │   │   ├── protocol.py
│   │   │   └── validation.py
│   │   ├── processing/
│   │   │   ├── __init__.py
│   │   │   ├── types.py
│   │   │   ├── ooxml_parser.py
│   │   │   ├── revision_resolver.py
│   │   │   ├── numbering_resolver.py
│   │   │   ├── clause_segmenter.py
│   │   │   ├── changed_clause_detector.py
│   │   │   └── validation_engine.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py
│   │   │   ├── party_extractor.py
│   │   │   ├── protocol_generator.py
│   │   │   ├── exporter.py
│   │   │   └── storage.py
│   │   └── workers/
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       └── tasks.py
│   └── tests/
│       ├── conftest.py
│       ├── processing/
│       ├── services/
│       ├── api/
│       ├── integration/
│       └── fixtures/
│           ├── __init__.py
│           └── builders.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.mjs
│   └── app/
│       ├── layout.tsx
│       ├── page.tsx
│       └── documents/[id]/
│           ├── analysis/page.tsx
│           ├── parties/page.tsx
│           ├── protocol/page.tsx
│           └── export/page.tsx
├── docker-compose.yml
└── README.md
```

---

## Task 0: Project bootstrap

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/document.py`
- Create: `backend/app/models/party.py`
- Create: `backend/app/models/clause.py`
- Create: `backend/app/models/protocol.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "disprot-backend"
version = "0.1.0"
description = "Disagreement protocol backend"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.115.0",
  "uvicorn[standard]==0.30.6",
  "pydantic==2.9.2",
  "pydantic-settings==2.5.2",
  "sqlalchemy==2.0.35",
  "alembic==1.13.3",
  "psycopg[binary]==3.2.3",
  "celery==5.4.0",
  "redis==5.1.1",
  "boto3==1.35.36",
  "python-multipart==0.0.12",
  "lxml==5.3.0",
  "python-docx==1.1.2",
  "docx-revisions==0.2.0",
  "docx2python==2.10.1",
  "docxtpl==0.18.0",
  "rapidfuzz==3.10.0",
  "diff-match-patch==20230430",
  "natasha==1.6.0",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.3",
  "pytest-cov==5.0.0",
  "pytest-asyncio==0.24.0",
  "httpx==0.27.2",
  "ruff==0.6.9",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: disprot
      POSTGRES_PASSWORD: disprot
      POSTGRES_DB: disprot
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: disprot
      MINIO_ROOT_PASSWORD: disprotsecret
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]

volumes:
  pgdata:
  miniodata:
```

- [ ] **Step 3: Create `.env.example`**

```
DATABASE_URL=postgresql+psycopg://disprot:disprot@localhost:5432/disprot
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=disprot
S3_SECRET_KEY=disprotsecret
S3_BUCKET=disprot
APP_ENV=local
```

- [ ] **Step 4: Create `backend/app/__init__.py`** (empty)

```python
```

- [ ] **Step 5: Create `backend/app/config.py`**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://disprot:disprot@localhost:5432/disprot"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "disprot"
    s3_secret_key: str = "disprotsecret"
    s3_bucket: str = "disprot"
    app_env: str = "local"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 6: Create `backend/app/db/__init__.py`** (empty)

```python
```

- [ ] **Step 7: Create `backend/app/db/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 8: Create `backend/app/db/session.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings

_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 9: Create `backend/app/models/__init__.py`**

```python
from app.models.document import Document
from app.models.party import Party
from app.models.clause import Clause
from app.models.protocol import Protocol, ProtocolRow

__all__ = ["Document", "Party", "Clause", "Protocol", "ProtocolRow"]
```

- [ ] **Step 10: Create `backend/app/models/enums.py`**

```python
import enum


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    PARTIES_CONFIRMED = "parties_confirmed"
    BUILT = "built"
    EXPORTED = "exported"
    FAILED = "failed"


class RevisionType(str, enum.Enum):
    INS = "INS"
    DEL = "DEL"
    FORMAT_ONLY = "FORMAT_ONLY"


class ClauseFlag(str, enum.Enum):
    MULTI_PARAGRAPH = "MULTI_PARAGRAPH"
    NEW_CLAUSE = "NEW_CLAUSE"
    DELETED_CLAUSE = "DELETED_CLAUSE"
    LOW_NUMBERING_CONFIDENCE = "LOW_NUMBERING_CONFIDENCE"
    LOW_CONFIDENCE_BOUNDARY = "LOW_CONFIDENCE_BOUNDARY"


class RowFlag(str, enum.Enum):
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MULTI_PARAGRAPH_SOURCE = "MULTI_PARAGRAPH_SOURCE"
    MANUALLY_ADDED = "MANUALLY_ADDED"
    USER_EDITED = "USER_EDITED"
```

- [ ] **Step 11: Create `backend/app/models/document.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base
from app.models.enums import DocumentStatus


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(512))
    storage_key: Mapped[str] = mapped_column(String(512))
    contract_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(SAEnum(DocumentStatus, name="document_status"), default=DocumentStatus.UPLOADED)
    drafting_party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    preflight_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Free-form pipeline metadata. Currently stores
    # {"preflight_diagnostics": [{level, component, code, message, block_id}, ...]}.
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 12: Create `backend/app/models/party.py`**

```python
import uuid
from sqlalchemy import String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(256), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
```

- [ ] **Step 13: Create `backend/app/models/clause.py`**

```python
import uuid
from sqlalchemy import String, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

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
```

- [ ] **Step 14: Create `backend/app/models/protocol.py`**

```python
import uuid
from sqlalchemy import String, ForeignKey, Integer, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY

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
```

- [ ] **Step 15: Create `backend/alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+psycopg://disprot:disprot@localhost:5432/disprot

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 16: Create `backend/alembic/env.py`**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import get_settings
from app.db.base import Base
from app.models import Document, Party, Clause, Protocol, ProtocolRow  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

- [ ] **Step 17: Create initial Alembic migration `backend/alembic/versions/0001_initial.py`**

```python
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
```

- [ ] **Step 18: Create `backend/tests/__init__.py`** (empty)

```python
```

- [ ] **Step 19: Create `backend/tests/conftest.py`**

```python
import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
```

- [ ] **Step 20: Bring services up and verify**

Run: `docker compose up -d postgres redis minio && cd backend && pip install -e ".[dev]" && alembic upgrade head`
Expected: containers running, `alembic upgrade head` reports `Running upgrade -> 0001`.

- [ ] **Step 21: Commit**

```bash
git add backend docker-compose.yml .env.example
git commit -m "chore: bootstrap backend skeleton + initial migration"
```

---

## Task 1: OOXMLParser

**Files:**
- Create: `backend/app/processing/__init__.py`
- Create: `backend/app/processing/types.py`
- Create: `backend/app/processing/ooxml_parser.py`
- Test: `backend/tests/processing/__init__.py`
- Test: `backend/tests/processing/test_ooxml_parser.py`
- Test: `backend/tests/fixtures/__init__.py`
- Test: `backend/tests/fixtures/builders.py`

- [ ] **Step 1: Create `backend/app/processing/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Create `backend/app/processing/types.py`** (shared dataclasses for the pipeline)

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ResolverDiagnostic:
    """Diagnostic emitted by a pipeline resolver/segmenter for the preflight report.

    Components: "numbering" | "revision" | "segmenter".

    The `code` field is the stable machine-readable classifier the
    ValidationEngine routes on. Without it, mapping diagnostics by
    `component` alone produces false positives — e.g. a benign
    format-only-revision diagnostic from the revision resolver would be
    surfaced to the user as a REVISION_MAPPING_MISMATCH warning. Defined
    codes (extend as new diagnostics are added):
      - "UNKNOWN_NUMID"        — numId on a paragraph not present in numbering.xml
      - "LOW_CONFIDENCE"       — numbering.confidence < 0.85
      - "FORMAT_ONLY_MISMATCH" — revisions exist but original_text==accepted_text
      - "MAPPING_MISMATCH"     — generic resolver could not map a block
    """
    level: Literal["warning", "error"]
    component: str
    code: str
    message: str
    block_id: str | None = None


@dataclass(frozen=True)
class Run:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class RawParagraph:
    block_id: str
    runs: tuple[Run, ...]
    num_id: int | None
    ilvl: int | None
    style_id: str | None
    is_in_table: bool = False

    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass(frozen=True)
class RawTableCell:
    paragraphs: tuple["RawParagraph", ...]

    def text(self) -> str:
        return " ".join(p.text() for p in self.paragraphs).strip()


@dataclass(frozen=True)
class RawTableRow:
    cells: tuple[RawTableCell, ...]


@dataclass(frozen=True)
class RawTable:
    block_id: str
    block_index: int
    rows: tuple[RawTableRow, ...]
    has_revisions: bool

    def cell_text(self) -> str:
        """Flattened text of all cells: joined by ' | ' across cells, '\\n' across rows."""
        return "\n".join(" | ".join(c.text() for c in r.cells) for r in self.rows)


@dataclass(frozen=True)
class RawDocument:
    blocks: tuple  # tuple[RawParagraph | RawTable, ...]


@dataclass(frozen=True)
class RevisionRecord:
    type: str   # "INS" | "DEL" | "FORMAT_ONLY"
    text: str
    author: str = ""


@dataclass(frozen=True)
class RevisionData:
    original_text: str
    accepted_text: str
    revisions: tuple[RevisionRecord, ...]


@dataclass(frozen=True)
class NumberingData:
    rendered_number: str | None
    confidence: float
    source: str   # "docx2python" | "regex" | "unmapped"


@dataclass(frozen=True)
class EnrichedParagraph:
    block_id: str
    text_runs: str
    num_id: int | None
    ilvl: int | None
    original_text: str
    accepted_text: str
    revisions: tuple[RevisionRecord, ...]
    rendered_number: str | None
    numbering_confidence: float


@dataclass
class Clause:
    clause_key: str
    label: str
    level: int
    parent_key: str | None
    paragraphs: list[EnrichedParagraph] = field(default_factory=list)
    tables: list[RawTable] = field(default_factory=list)
    children: list["Clause"] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
```

- [ ] **Step 3: Create `backend/tests/fixtures/builders.py`** — minimal DOCX builder using `python-docx` plus raw OOXML injection for revisions

```python
from io import BytesIO
from docx import Document as DocxDocument
from docx.oxml.ns import qn
from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def build_simple_docx(paragraphs: list[str]) -> bytes:
    doc = DocxDocument()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_insertion(before: str, inserted: str, after: str, author: str = "Editor") -> bytes:
    """Build a DOCX where `inserted` is wrapped in <w:ins>."""
    doc = DocxDocument()
    p = doc.add_paragraph(before)
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), author)
    ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t"))
    t.text = inserted
    t.set(qn("xml:space"), "preserve")
    if after:
        r2 = etree.SubElement(pelem, qn("w:r"))
        t2 = etree.SubElement(r2, qn("w:t"))
        t2.text = after
        t2.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_table(rows: list[list[str]], leading_paragraph: str = "") -> bytes:
    """Build a DOCX with one table whose cells contain the given strings."""
    doc = DocxDocument()
    if leading_paragraph:
        doc.add_paragraph(leading_paragraph)
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows) if rows else 0
    table = doc.add_table(rows=n_rows, cols=n_cols)
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            table.cell(r_idx, c_idx).text = val
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_docx_with_deletion(before: str, deleted: str, after: str, author: str = "Editor") -> bytes:
    """Build a DOCX where `deleted` is wrapped in <w:del>/<w:delText>."""
    doc = DocxDocument()
    p = doc.add_paragraph(before)
    pelem = p._p
    deln = etree.SubElement(pelem, qn("w:del"))
    deln.set(qn("w:id"), "1")
    deln.set(qn("w:author"), author)
    deln.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(deln, qn("w:r"))
    t = etree.SubElement(r, qn("w:delText"))
    t.text = deleted
    t.set(qn("xml:space"), "preserve")
    if after:
        r2 = etree.SubElement(pelem, qn("w:r"))
        t2 = etree.SubElement(r2, qn("w:t"))
        t2.text = after
        t2.set(qn("xml:space"), "preserve")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
```

- [ ] **Step 4: Create `backend/tests/processing/__init__.py`** and `backend/tests/fixtures/__init__.py` (both empty)

```python
```

- [ ] **Step 5: Write the failing test `backend/tests/processing/test_ooxml_parser.py`**

```python
from app.processing.ooxml_parser import OOXMLParser
from app.processing.types import RawParagraph, RawDocument
from tests.fixtures.builders import build_simple_docx


def test_parse_returns_raw_document_with_paragraphs():
    data = build_simple_docx(["Hello", "World"])
    doc = OOXMLParser().parse(data)
    assert isinstance(doc, RawDocument)
    paragraphs = [b for b in doc.blocks if isinstance(b, RawParagraph)]
    assert len(paragraphs) == 2
    assert paragraphs[0].text() == "Hello"
    assert paragraphs[1].text() == "World"
    assert paragraphs[0].block_id == "p_0001"
    assert paragraphs[1].block_id == "p_0002"


def test_parse_preserves_text_inside_w_ins():
    from tests.fixtures.builders import build_docx_with_insertion
    data = build_docx_with_insertion("before ", "INSERTED", " after")
    doc = OOXMLParser().parse(data)
    paragraphs = [b for b in doc.blocks if isinstance(b, RawParagraph)]
    assert paragraphs[0].text() == "before INSERTED after"


def test_parse_emits_raw_table_with_rows_and_cells():
    from app.processing.types import RawTable
    from tests.fixtures.builders import build_docx_with_table
    data = build_docx_with_table(
        rows=[["A1", "B1"], ["A2", "B2"]],
        leading_paragraph="Перед таблицей",
    )
    doc = OOXMLParser().parse(data)
    tables = [b for b in doc.blocks if isinstance(b, RawTable)]
    assert len(tables) == 1
    t = tables[0]
    assert t.block_id == "t_0001"
    assert t.block_index == 1  # one paragraph at index 0, table at index 1
    assert len(t.rows) == 2
    assert len(t.rows[0].cells) == 2
    assert t.rows[0].cells[0].text() == "A1"
    assert t.rows[1].cells[1].text() == "B2"
    # Each cell holds RawParagraph objects flagged as is_in_table.
    assert t.rows[0].cells[0].paragraphs[0].is_in_table is True
```

- [ ] **Step 6: Run the test, expect failure**

Run: `cd backend && pytest tests/processing/test_ooxml_parser.py -v`
Expected: ImportError / ModuleNotFoundError on `app.processing.ooxml_parser`.

- [ ] **Step 7: Implement `backend/app/processing/ooxml_parser.py`**

```python
from __future__ import annotations
import zipfile
from io import BytesIO
from lxml import etree

from app.processing.types import RawDocument, RawParagraph, RawTable, RawTableCell, RawTableRow, Run

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


class OOXMLParser:
    def parse(self, data: bytes) -> RawDocument:
        with zipfile.ZipFile(BytesIO(data)) as z:
            with z.open("word/document.xml") as f:
                tree = etree.parse(f)
        body = tree.getroot().find(f"{{{W_NS}}}body")
        if body is None:
            return RawDocument(blocks=())
        blocks: list = []
        p_idx = 0
        t_idx = 0
        block_idx = 0
        for child in body:
            tag = etree.QName(child.tag).localname
            if tag == "p":
                p_idx += 1
                blocks.append(self._parse_paragraph(child, f"p_{p_idx:04d}", is_in_table=False))
                block_idx += 1
            elif tag == "tbl":
                t_idx += 1
                blocks.append(self._parse_table(child, f"t_{t_idx:04d}", block_idx))
                block_idx += 1
        return RawDocument(blocks=tuple(blocks))

    def _parse_paragraph(self, p_elem, block_id: str, is_in_table: bool) -> RawParagraph:
        runs: list[Run] = []
        for r in p_elem.iter(f"{{{W_NS}}}r"):
            text_parts: list[str] = []
            for t in r.iter():
                local = etree.QName(t.tag).localname
                if local in ("t", "delText") and t.text:
                    text_parts.append(t.text)
                elif local == "tab":
                    text_parts.append("\t")
                elif local == "br":
                    text_parts.append("\n")
            txt = "".join(text_parts)
            if not txt:
                continue
            rpr = r.find(f"{{{W_NS}}}rPr")
            bold = rpr is not None and rpr.find(f"{{{W_NS}}}b") is not None
            italic = rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None
            if runs and runs[-1].bold == bold and runs[-1].italic == italic:
                runs[-1] = Run(text=runs[-1].text + txt, bold=bold, italic=italic)
            else:
                runs.append(Run(text=txt, bold=bold, italic=italic))
        ppr = p_elem.find(f"{{{W_NS}}}pPr")
        num_id = None
        ilvl = None
        style_id = None
        if ppr is not None:
            num_pr = ppr.find(f"{{{W_NS}}}numPr")
            if num_pr is not None:
                ni = num_pr.find(f"{{{W_NS}}}numId")
                il = num_pr.find(f"{{{W_NS}}}ilvl")
                if ni is not None and ni.get(f"{{{W_NS}}}val") is not None:
                    num_id = int(ni.get(f"{{{W_NS}}}val"))
                if il is not None and il.get(f"{{{W_NS}}}val") is not None:
                    ilvl = int(il.get(f"{{{W_NS}}}val"))
            ps = ppr.find(f"{{{W_NS}}}pStyle")
            if ps is not None:
                style_id = ps.get(f"{{{W_NS}}}val")
        return RawParagraph(
            block_id=block_id,
            runs=tuple(runs),
            num_id=num_id,
            ilvl=ilvl,
            style_id=style_id,
            is_in_table=is_in_table,
        )

    def _parse_table(self, tbl_elem, block_id: str, block_index: int) -> RawTable:
        has_revisions = (
            tbl_elem.find(f".//{{{W_NS}}}ins") is not None
            or tbl_elem.find(f".//{{{W_NS}}}del") is not None
        )
        rows: list[RawTableRow] = []
        cell_p_counter = 0
        for tr in tbl_elem.findall(f"{{{W_NS}}}tr"):
            cells: list[RawTableCell] = []
            for tc in tr.findall(f"{{{W_NS}}}tc"):
                cell_paragraphs: list[RawParagraph] = []
                for p in tc.findall(f"{{{W_NS}}}p"):
                    cell_p_counter += 1
                    cell_pid = f"{block_id}_p_{cell_p_counter:04d}"
                    cell_paragraphs.append(
                        self._parse_paragraph(p, cell_pid, is_in_table=True)
                    )
                cells.append(RawTableCell(paragraphs=tuple(cell_paragraphs)))
            rows.append(RawTableRow(cells=tuple(cells)))
        return RawTable(
            block_id=block_id,
            block_index=block_index,
            rows=tuple(rows),
            has_revisions=has_revisions,
        )
```

- [ ] **Step 8: Run the test, expect pass**

Run: `cd backend && pytest tests/processing/test_ooxml_parser.py -v`
Expected: 3 passed.

- [ ] **Step 9: Commit**

```bash
git add backend/app/processing backend/tests/processing backend/tests/fixtures
git commit -m "feat(processing): add OOXMLParser with run coalescing and table flag"
```

---

## Task 2: RevisionResolver

**Files:**
- Create: `backend/app/processing/revision_resolver.py`
- Test: `backend/tests/processing/test_revision_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.types import RawParagraph
from tests.fixtures.builders import build_docx_with_insertion, build_docx_with_deletion, build_simple_docx


def test_resolve_insertion_yields_original_without_inserted_text():
    data = build_docx_with_insertion("before ", "INSERTED", " after")
    raw = OOXMLParser().parse(data)
    rmap, diags = RevisionResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    rd = rmap[p.block_id]
    assert rd.original_text == "before  after"
    assert rd.accepted_text == "before INSERTED after"
    assert any(rev.type == "INS" and rev.text == "INSERTED" for rev in rd.revisions)
    assert diags == []


def test_resolve_deletion_yields_original_with_deleted_text_and_accepted_without():
    data = build_docx_with_deletion("before ", "DELETED", " after")
    raw = OOXMLParser().parse(data)
    rmap, diags = RevisionResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    rd = rmap[p.block_id]
    assert rd.original_text == "before DELETED after"
    assert rd.accepted_text == "before  after"
    assert any(rev.type == "DEL" and rev.text == "DELETED" for rev in rd.revisions)
    assert diags == []


def test_resolve_no_revisions_yields_identical_texts():
    data = build_simple_docx(["Plain paragraph"])
    raw = OOXMLParser().parse(data)
    rmap, diags = RevisionResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    rd = rmap[p.block_id]
    assert rd.original_text == "Plain paragraph"
    assert rd.accepted_text == "Plain paragraph"
    assert rd.revisions == ()
    assert diags == []
```

- [ ] **Step 2: Run the test, expect failure**

Run: `cd backend && pytest tests/processing/test_revision_resolver.py -v`
Expected: ModuleNotFoundError on `app.processing.revision_resolver`.

- [ ] **Step 3: Implement `backend/app/processing/revision_resolver.py`** (own implementation, no external `docx-revisions` dependency at this layer — we already have the XML)

```python
from __future__ import annotations
import zipfile
from io import BytesIO
from lxml import etree

from app.processing.types import (
    RawDocument, RawParagraph, ResolverDiagnostic, RevisionData, RevisionRecord,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

RevisionResolveResult = tuple[dict[str, RevisionData], list[ResolverDiagnostic]]


class RevisionResolver:
    """Build original_text / accepted_text for each top-level paragraph from <w:ins> / <w:del>."""

    def resolve(self, data: bytes, raw_doc: RawDocument) -> RevisionResolveResult:
        with zipfile.ZipFile(BytesIO(data)) as z:
            with z.open("word/document.xml") as f:
                tree = etree.parse(f)
        body = tree.getroot().find(f"{{{W_NS}}}body")
        out: dict[str, RevisionData] = {}
        diags: list[ResolverDiagnostic] = []
        if body is None:
            return out, diags
        para_blocks = [b for b in raw_doc.blocks if isinstance(b, RawParagraph)]
        body_paragraphs = [c for c in body if etree.QName(c.tag).localname == "p"]
        for raw_p, p_elem in zip(para_blocks, body_paragraphs):
            rd = self._paragraph_revision(p_elem)
            out[raw_p.block_id] = rd
            # Format-only mismatch: revision elements present but original/accepted equal.
            if rd.revisions and rd.original_text == rd.accepted_text:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="revision",
                    code="FORMAT_ONLY_MISMATCH",
                    message="format-only revisions detected (original==accepted)",
                    block_id=raw_p.block_id,
                ))
        for raw_p in para_blocks[len(body_paragraphs):]:
            out[raw_p.block_id] = RevisionData(
                original_text=raw_p.text(), accepted_text=raw_p.text(), revisions=(),
            )
        return out, diags

    def _paragraph_revision(self, p_elem) -> RevisionData:
        original_parts: list[str] = []
        accepted_parts: list[str] = []
        revisions: list[RevisionRecord] = []
        for child in p_elem.iter():
            local = etree.QName(child.tag).localname
            if local == "ins":
                ins_text = "".join(
                    (t.text or "")
                    for t in child.iter(f"{{{W_NS}}}t")
                )
                if ins_text:
                    accepted_parts.append(ins_text)
                    revisions.append(RevisionRecord(type="INS", text=ins_text, author=child.get(f"{{{W_NS}}}author") or ""))
            elif local == "del":
                del_text = "".join(
                    (t.text or "")
                    for t in child.iter(f"{{{W_NS}}}delText")
                )
                if del_text:
                    original_parts.append(del_text)
                    revisions.append(RevisionRecord(type="DEL", text=del_text, author=child.get(f"{{{W_NS}}}author") or ""))
            elif local == "r":
                if any(etree.QName(p.tag).localname in ("ins", "del") for p in child.iterancestors()):
                    continue
                run_text = "".join(
                    (t.text or "")
                    for t in child.iter(f"{{{W_NS}}}t")
                )
                if run_text:
                    original_parts.append(run_text)
                    accepted_parts.append(run_text)
        return RevisionData(
            original_text="".join(original_parts),
            accepted_text="".join(accepted_parts),
            revisions=tuple(revisions),
        )
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd backend && pytest tests/processing/test_revision_resolver.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/processing/revision_resolver.py backend/tests/processing/test_revision_resolver.py
git commit -m "feat(processing): add RevisionResolver building original/accepted text"
```

---

## Task 3: NumberingResolver

**Files:**
- Create: `backend/app/processing/numbering_resolver.py`
- Test: `backend/tests/processing/test_numbering_resolver.py`
- Modify: `backend/tests/fixtures/builders.py` (add a numbered-list builder)

- [ ] **Step 1: Extend `backend/tests/fixtures/builders.py` with `build_docx_with_manual_numbering` and `build_docx_with_unknown_numid`**

Append to file:

```python
def build_docx_with_manual_numbering(items: list[str]) -> bytes:
    """Items already include literal numbers like '1.', '1.1.', '2.'."""
    return build_simple_docx(items)


def build_docx_with_unknown_numid(text: str, num_id: int = 999) -> bytes:
    """Build a DOCX where a paragraph references a numId that does not exist in numbering.xml."""
    doc = DocxDocument()
    p = doc.add_paragraph(text)
    pPr = p._p.get_or_add_pPr()
    numPr = etree.SubElement(pPr, qn("w:numPr"))
    ilvl = etree.SubElement(numPr, qn("w:ilvl"))
    ilvl.set(qn("w:val"), "0")
    numId = etree.SubElement(numPr, qn("w:numId"))
    numId.set(qn("w:val"), str(num_id))
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
```

- [ ] **Step 2: Write the failing test `backend/tests/processing/test_numbering_resolver.py`**

```python
from app.processing.ooxml_parser import OOXMLParser
from app.processing.numbering_resolver import NumberingResolver
from app.processing.types import RawParagraph
from tests.fixtures.builders import build_docx_with_manual_numbering


def test_regex_fallback_extracts_dotted_numbers():
    data = build_docx_with_manual_numbering([
        "1. Предмет договора",
        "1.1. Исполнитель обязуется",
        "2. Цена договора",
    ])
    raw = OOXMLParser().parse(data)
    nmap, diags = NumberingResolver().resolve(data, raw)
    paragraphs = [b for b in raw.blocks if isinstance(b, RawParagraph)]
    assert nmap[paragraphs[0].block_id].rendered_number == "1."
    assert nmap[paragraphs[1].block_id].rendered_number == "1.1."
    assert nmap[paragraphs[2].block_id].rendered_number == "2."
    assert nmap[paragraphs[0].block_id].source == "regex"
    assert nmap[paragraphs[0].block_id].confidence == 0.7
    # regex confidence is 0.7 < 0.85 threshold → low-confidence diagnostics emitted.
    assert any(d.component == "numbering" and "low confidence" in d.message for d in diags)


def test_unnumbered_paragraph_gets_unmapped():
    data = build_docx_with_manual_numbering(["Просто текст без номера"])
    raw = OOXMLParser().parse(data)
    nmap, _ = NumberingResolver().resolve(data, raw)
    p = next(b for b in raw.blocks if isinstance(b, RawParagraph))
    nd = nmap[p.block_id]
    assert nd.rendered_number is None
    assert nd.confidence == 0.0
    assert nd.source == "unmapped"


def test_unknown_numid_emits_diagnostic():
    """A paragraph whose numPr references a numId not in numbering.xml emits a warning."""
    from tests.fixtures.builders import build_docx_with_unknown_numid
    data = build_docx_with_unknown_numid("Пункт со сломанной нумерацией", num_id=999)
    raw = OOXMLParser().parse(data)
    _, diags = NumberingResolver().resolve(data, raw)
    assert any(
        d.component == "numbering" and "numId 999 not found" in d.message
        for d in diags
    )
```

- [ ] **Step 3: Run the test, expect failure**

Run: `cd backend && pytest tests/processing/test_numbering_resolver.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement `backend/app/processing/numbering_resolver.py`**

```python
from __future__ import annotations
import re
import zipfile
from io import BytesIO
from lxml import etree

from app.processing.types import (
    NumberingData, RawDocument, RawParagraph, ResolverDiagnostic,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REGEX_NUMBER = re.compile(r"^\s*(?:Статья\s+)?(\d+(?:\.\d+)*\.?)\s+", re.IGNORECASE)
LOW_CONFIDENCE_THRESHOLD = 0.85

NumberingResolveResult = tuple[dict[str, NumberingData], list[ResolverDiagnostic]]


class NumberingResolver:
    """Resolve a rendered_number string for each paragraph.

    v1 strategy: try docx2python; on miss, fall back to regex on paragraph text.
    Returns (mapping, diagnostics) where diagnostics flag missing numIds and
    paragraphs whose numbering confidence is below the 0.85 threshold.
    """

    def resolve(self, data: bytes, raw_doc: RawDocument) -> NumberingResolveResult:
        para_blocks = [b for b in raw_doc.blocks if isinstance(b, RawParagraph)]
        d2p_numbers = self._docx2python_numbers(data, len(para_blocks))
        known_num_ids = self._known_num_ids(data)
        out: dict[str, NumberingData] = {}
        diags: list[ResolverDiagnostic] = []
        counters: dict[int, int] = {}
        for idx, p in enumerate(para_blocks):
            if p.num_id is not None and p.num_id not in known_num_ids:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="UNKNOWN_NUMID",
                    message=f"numId {p.num_id} not found in numbering.xml",
                    block_id=p.block_id,
                ))
            d2p = d2p_numbers.get(idx)
            if d2p:
                out[p.block_id] = NumberingData(rendered_number=d2p, confidence=1.0, source="docx2python")
                continue
            m = REGEX_NUMBER.match(p.text())
            if m:
                num = m.group(1)
                if not num.endswith("."):
                    num += "."
                out[p.block_id] = NumberingData(rendered_number=num, confidence=0.7, source="regex")
                continue
            if p.num_id is not None:
                lvl = (p.ilvl or 0) + 1
                counters[lvl] = counters.get(lvl, 0) + 1
                for higher in list(counters):
                    if higher > lvl:
                        del counters[higher]
                rendered = ".".join(str(counters.get(i, 1)) for i in range(1, lvl + 1)) + "."
                out[p.block_id] = NumberingData(rendered_number=rendered, confidence=0.5, source="regex")
            else:
                out[p.block_id] = NumberingData(rendered_number=None, confidence=0.0, source="unmapped")
        for p in para_blocks:
            nd = out[p.block_id]
            if nd.rendered_number is not None and nd.confidence < LOW_CONFIDENCE_THRESHOLD:
                diags.append(ResolverDiagnostic(
                    level="warning",
                    component="numbering",
                    code="LOW_CONFIDENCE",
                    message=f"low confidence for paragraph {p.block_id} ({nd.confidence:.2f})",
                    block_id=p.block_id,
                ))
        return out, diags

    def _known_num_ids(self, data: bytes) -> set[int]:
        """Read numbering.xml and return the set of numId values defined there."""
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                if "word/numbering.xml" not in z.namelist():
                    return set()
                with z.open("word/numbering.xml") as f:
                    tree = etree.parse(f)
        except Exception:
            return set()
        out: set[int] = set()
        for num in tree.getroot().iter(f"{{{W_NS}}}num"):
            val = num.get(f"{{{W_NS}}}numId")
            if val is not None:
                try:
                    out.add(int(val))
                except ValueError:
                    pass
        return out

    def _docx2python_numbers(self, data: bytes, expected: int) -> dict[int, str]:
        """Best-effort docx2python integration. Returns {paragraph_index: rendered_number}.

        If docx2python is not callable on this content, returns {}.
        """
        try:
            from docx2python import docx2python  # type: ignore
        except Exception:
            return {}
        try:
            with zipfile.ZipFile(BytesIO(data)) as z:
                names = z.namelist()
            if "word/numbering.xml" not in names:
                return {}
            result = docx2python(BytesIO(data), html=False)
            numbers: dict[int, str] = {}
            idx = 0
            for body_part in result.body:
                for table in body_part:
                    for row in table:
                        for cell in row:
                            for para in cell:
                                if isinstance(para, str) and para.strip():
                                    m = re.match(r"^\s*(\d+(?:\.\d+)*\.?)\s+", para)
                                    if m:
                                        numbers[idx] = m.group(1) if m.group(1).endswith(".") else m.group(1) + "."
                                    idx += 1
                                    if idx >= expected:
                                        return numbers
            return numbers
        except Exception:
            return {}
```

- [ ] **Step 5: Run the test, expect pass**

Run: `cd backend && pytest tests/processing/test_numbering_resolver.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/processing/numbering_resolver.py backend/tests/processing/test_numbering_resolver.py backend/tests/fixtures/builders.py
git commit -m "feat(processing): add NumberingResolver with regex fallback"
```

---

## Task 4: ClauseSegmenter

**Files:**
- Create: `backend/app/processing/clause_segmenter.py`
- Test: `backend/tests/processing/test_clause_segmenter.py`

- [ ] **Step 1: Write the failing test**

```python
from app.processing.types import EnrichedParagraph, Clause, RawTable, RawTableRow, RawTableCell
from app.processing.clause_segmenter import ClauseSegmenter


def _ep(block_id: str, text: str, num: str | None, level: int | None) -> EnrichedParagraph:
    return EnrichedParagraph(
        block_id=block_id,
        text_runs=text,
        num_id=1 if num else None,
        ilvl=level,
        original_text=text,
        accepted_text=text,
        revisions=(),
        rendered_number=num,
        numbering_confidence=1.0 if num else 0.0,
    )


def _table(block_id: str, block_index: int, has_revisions: bool = False) -> RawTable:
    return RawTable(
        block_id=block_id,
        block_index=block_index,
        rows=(RawTableRow(cells=(RawTableCell(paragraphs=()),)),),
        has_revisions=has_revisions,
    )


def test_segments_top_level_numbered_paragraphs():
    paras = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert [c.label for c in clauses] == ["1.", "2."]
    assert all(c.level == 0 for c in clauses)


def test_continuation_paragraph_attaches_to_current_clause():
    paras = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Дополнительное предложение.", None, None),
        _ep("p_0003", "2. Цена", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert len(clauses) == 2
    assert len(clauses[0].paragraphs) == 2
    assert "MULTI_PARAGRAPH" in clauses[0].flags


def test_nested_numbering_builds_parent_links():
    paras = [
        _ep("p_0001", "1. Раздел", "1.", 0),
        _ep("p_0002", "1.1. Подпункт", "1.1.", 1),
        _ep("p_0003", "2. Раздел два", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert len(clauses) == 3
    by_label = {c.label: c for c in clauses}
    assert by_label["1.1."].parent_key == by_label["1."].clause_key
    assert by_label["2."].parent_key is None


def test_preamble_collects_unnumbered_prefix():
    paras = [
        _ep("p_0001", "Договор № 5", None, None),
        _ep("p_0002", "ООО Ромашка, в лице ...", None, None),
        _ep("p_0003", "1. Предмет", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(paras)
    assert clauses[0].label == "Преамбула"
    assert len(clauses[0].paragraphs) == 2
    assert clauses[1].label == "1."


def test_table_inside_clause_attaches_to_current_clause():
    """A RawTable that appears between two paragraphs of clause 1 attaches to clause 1."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _table("t_0001", block_index=1),
        _ep("p_0002", "Продолжение пункта 1", None, None),
        _ep("p_0003", "2. Цена", "2.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    assert len(clauses) == 2
    assert clauses[0].label == "1."
    assert len(clauses[0].tables) == 1
    assert clauses[0].tables[0].block_id == "t_0001"
    assert clauses[1].label == "2."
    assert clauses[1].tables == []


def test_standalone_table_outside_any_clause_gets_its_own_clause_with_flag():
    """A RawTable before the first numbered clause produces a standalone Таблица clause."""
    blocks = [
        _table("t_0001", block_index=0),
        _ep("p_0001", "1. Предмет", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    table_clauses = [c for c in clauses if c.label == "Таблица"]
    assert len(table_clauses) == 1
    assert "STANDALONE_TABLE" in table_clauses[0].flags
    assert len(table_clauses[0].tables) == 1
    assert table_clauses[0].tables[0].block_id == "t_0001"


def test_table_after_requisites_heading_attaches_to_requisites_clause():
    """A RawTable that appears after the "Реквизиты сторон" heading must attach
    to the requisites clause — not to the previous numbered clause and not as
    a standalone STANDALONE_TABLE clause. The segmenter pre-scans the last 30
    top-level paragraphs (or all paragraphs if fewer than 30) and picks the
    FIRST paragraph in that window matching the requisites pattern. With only
    6 paragraphs total here the entire document is the tail window, so the
    heading at index 2 is found."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
        _ep("p_0003", "Реквизиты сторон", None, None),
        _table("t_0001", block_index=3),
        _ep("p_0004", "ООО Ромашка, ИНН 7700000000, ...", None, None),
        _ep("p_0005", "ООО Лютик, ИНН 7700000001, ...", None, None),
        _ep("p_0006", "Контактное лицо: ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    req = requisites[0]
    # The heading paragraph, the table, and the trailing paragraphs all land
    # in the requisites clause.
    assert len(req.tables) == 1
    assert req.tables[0].block_id == "t_0001"
    assert len(req.paragraphs) == 4
    assert [p.block_id for p in req.paragraphs] == [
        "p_0003",
        "p_0004",
        "p_0005",
        "p_0006",
    ]
    # The previous numbered clauses must not pick up the table.
    for label in ("1.", "2."):
        clause_n = next(c for c in clauses if c.label == label)
        assert clause_n.tables == []
    # No STANDALONE_TABLE clause was emitted.
    assert not any("STANDALONE_TABLE" in c.flags for c in clauses)


def test_signatures_heading_variant_also_starts_requisites_clause():
    """A "Подписи сторон" heading is a common alternative to "Реквизиты сторон"
    and must trigger the same requisites-section behaviour: the heading
    paragraph itself plus every following block (table + trailing paragraph)
    all land in a single clause labelled "Реквизиты сторон". The tail-window
    pre-scan picks up the heading by full-paragraph regex match (the document
    has fewer than 30 paragraphs total, so the entire document is the tail
    window)."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
        _ep("p_0003", "Подписи сторон", None, None),
        _table("t_0001", block_index=3),
        _ep("p_0004", "ООО Ромашка, ИНН 7700000000, ...", None, None),
        _ep("p_0005", "ООО Лютик, ИНН 7700000001, ...", None, None),
        _ep("p_0006", "Контактное лицо: ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    req = requisites[0]
    assert len(req.paragraphs) == 4
    assert [p.block_id for p in req.paragraphs] == [
        "p_0003",
        "p_0004",
        "p_0005",
        "p_0006",
    ]
    assert len(req.tables) == 1
    assert req.tables[0].block_id == "t_0001"
    assert not any("STANDALONE_TABLE" in c.flags for c in clauses)


def test_mid_document_requisites_phrase_does_not_trigger_requisites_mode():
    """A paragraph containing the substring "реквизит" mid-document — e.g.
    "В случае изменения реквизитов стороны" — must NOT switch the segmenter
    into requisites mode. The next numbered paragraph is parsed as a normal
    clause, not as a continuation of a (non-existent) requisites clause.

    This is enforced by anchoring `_REQUISITES_RE` to full-paragraph matches
    with `^…$`: the substring "реквизитов" inside a longer sentence does not
    match, so the tail-window pre-scan returns `last_requisites_idx = None`
    and requisites mode never activates.
    """
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "В случае изменения реквизитов стороны", None, None),
        _ep("p_0003", "2. Цена", "2.", 0),
        _ep("p_0004", "3. Сроки", "3.", 0),
        _ep("p_0005", "4. Ответственность", "4.", 0),
        _ep("p_0006", "5. Прочее", "5.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    # No requisites clause was emitted.
    assert not any(c.label == "Реквизиты сторон" for c in clauses)
    # Clause 2. is a normal clause, not absorbed into a requisites section.
    labels = [c.label for c in clauses]
    assert labels == ["1.", "2.", "3.", "4.", "5."]
    # The mid-document "изменения реквизитов" phrase attached as a
    # continuation paragraph of clause 1.
    clause_one = next(c for c in clauses if c.label == "1.")
    assert any("изменения реквизитов" in p.text_runs for p in clause_one.paragraphs)


def test_small_doc_requisites_at_middle_position_still_found():
    """For a tiny document (5 paragraphs total) the tail window is the
    whole document, so a "Реквизиты сторон" heading at index 2 still
    activates requisites mode and absorbs everything after it."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "2. Цена", "2.", 0),
        _ep("p_0003", "Реквизиты сторон", None, None),
        _ep("p_0004", "ООО Ромашка, ИНН 7700000000", None, None),
        _ep("p_0005", "АО Василёк, ИНН 7700000001", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    assert [p.block_id for p in requisites[0].paragraphs] == ["p_0003", "p_0004", "p_0005"]


def test_multiple_requisites_headings_uses_first_in_tail_window():
    """When the document has multiple requisites-style headings near the end
    (e.g. "Реквизиты" then "Подписи сторон"), the FIRST heading in the
    last-30-paragraph window is chosen. Once requisites mode opens, it
    never closes — the later "Подписи сторон" paragraph is just absorbed
    into the same clause."""
    # 32 paragraphs total: 25 numbered clauses, then "Реквизиты" at index
    # 25, two filler paragraphs, "Подписи сторон" at index 28, and three
    # trailing paragraphs.
    blocks: list = [_ep(f"p_{i:04d}", f"{i + 1}. п", f"{i + 1}.", 0) for i in range(25)]
    blocks.append(_ep("p_0025", "Реквизиты", None, None))           # index 25
    blocks.append(_ep("p_0026", "ООО Ромашка ...", None, None))
    blocks.append(_ep("p_0027", "АО Василёк ...", None, None))
    blocks.append(_ep("p_0028", "Подписи сторон", None, None))      # index 28
    blocks.append(_ep("p_0029", "________________", None, None))
    blocks.append(_ep("p_0030", "________________", None, None))
    blocks.append(_ep("p_0031", "Дата: ...", None, None))
    clauses = ClauseSegmenter().segment(blocks)
    # Exactly one requisites clause; opens at the FIRST heading (index 25).
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    req = requisites[0]
    # All blocks from index 25 onward (including the later "Подписи сторон"
    # heading) are absorbed into this single requisites clause.
    assert [p.block_id for p in req.paragraphs] == [
        "p_0025", "p_0026", "p_0027", "p_0028", "p_0029", "p_0030", "p_0031",
    ]


def test_mid_document_heading_outside_tail_window_ignored():
    """A "Реквизиты сторон" heading at paragraph index 5 of a 41-paragraph
    document falls outside the last-30-paragraph tail window. With no
    matching heading in the window, requisites mode does not activate
    and the heading paragraph is absorbed as a plain continuation of the
    enclosing clause."""
    blocks: list = [_ep("p_0000", "1. Предмет", "1.", 0)]
    blocks.append(_ep("p_0001", "Лирическое отступление", None, None))
    blocks.append(_ep("p_0002", "ещё немного", None, None))
    blocks.append(_ep("p_0003", "продолжение", None, None))
    blocks.append(_ep("p_0004", "финал отступления", None, None))
    blocks.append(_ep("p_0005", "Реквизиты сторон", None, None))    # index 5: outside window
    # 35 more numbered paragraphs (clauses 2..36) — none match
    # _REQUISITES_RE, so the tail window contains no requisites heading.
    for k in range(2, 37):
        blocks.append(_ep(f"p_{k + 4:04d}", f"{k}. п", f"{k}.", 0))
    clauses = ClauseSegmenter().segment(blocks)
    assert not any(c.label == "Реквизиты сторон" for c in clauses)
    # Clause "1." absorbed the false heading as a continuation paragraph.
    clause_one = next(c for c in clauses if c.label == "1.")
    assert any(p.text_runs == "Реквизиты сторон" for p in clause_one.paragraphs)


def test_signatures_and_requisites_combined_heading_triggers_requisites_mode():
    """The composite heading "Подписи и реквизиты сторон" is a very common
    Russian-contract variant and must activate requisites mode."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Подписи и реквизиты сторон", None, None),
        _ep("p_0003", "ООО Ромашка ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    assert [p.block_id for p in requisites[0].paragraphs] == ["p_0002", "p_0003"]


def test_addresses_and_requisites_combined_heading_triggers_requisites_mode():
    """The composite heading "Адреса и реквизиты сторон" must also activate
    requisites mode."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Адреса и реквизиты сторон", None, None),
        _ep("p_0003", "ООО Ромашка, г. Москва ...", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    requisites = [c for c in clauses if c.label == "Реквизиты сторон"]
    assert len(requisites) == 1
    assert [p.block_id for p in requisites[0].paragraphs] == ["p_0002", "p_0003"]


def test_annex_section_prefixes_subsequent_numbered_clauses():
    """An "Приложение № N" heading opens an annex section. Numbered clauses
    that follow are relabelled with the annex prefix
    ("Приложение № 1, п. 1", "Приложение № 1, п. 2", ...). A new
    "Приложение № N" heading resets the prefix to that new annex.
    """
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Приложение № 1", None, None),
        _ep("p_0003", "1. Перечень оборудования", "1.", 0),
        _ep("p_0004", "2. Стоимость", "2.", 0),
        _ep("p_0005", "Приложение № 2", None, None),
        _ep("p_0006", "1. Сроки поставки", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    labels = [c.label for c in clauses]
    # The base contract clause "1." stays bare. Annex headings appear
    # verbatim. Numbered clauses inside an annex are prefixed.
    assert labels == [
        "1.",
        "Приложение № 1",
        "Приложение № 1, п. 1",
        "Приложение № 1, п. 2",
        "Приложение № 2",
        "Приложение № 2, п. 1",
    ]
    by_label = {c.label: c for c in clauses}
    # The annex header is a top-level clause (parent_key=None).
    assert by_label["Приложение № 1"].parent_key is None
    # Numbered clauses inside an annex hang off the annex header — they
    # must NOT be top-level (parent_key=None) or the document tree loses
    # the annex grouping.
    assert (
        by_label["Приложение № 1, п. 1"].parent_key
        == by_label["Приложение № 1"].clause_key
    )
    assert (
        by_label["Приложение № 1, п. 2"].parent_key
        == by_label["Приложение № 1"].clause_key
    )
    # A new annex resets the parent for its own children.
    assert (
        by_label["Приложение № 2, п. 1"].parent_key
        == by_label["Приложение № 2"].clause_key
    )


def test_annex_unnumbered_paragraph_attaches_to_current_annex_clause():
    """An unnumbered paragraph that follows a numbered annex clause must
    attach to that numbered clause as a continuation paragraph (same rule
    as for non-annex clauses)."""
    blocks = [
        _ep("p_0001", "Приложение № 1", None, None),
        _ep("p_0002", "1. Перечень оборудования", "1.", 0),
        _ep("p_0003", "Дополнительное описание", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    by_label = {c.label: c for c in clauses}
    annex_clause_1 = by_label["Приложение № 1, п. 1"]
    assert [p.block_id for p in annex_clause_1.paragraphs] == ["p_0002", "p_0003"]
    assert "MULTI_PARAGRAPH" in annex_clause_1.flags


def test_annex_unnumbered_paragraph_between_annex_header_and_first_clause_attaches_to_header():
    """An unnumbered paragraph after the annex heading but before the first
    numbered clause inside the annex attaches to the annex header — not to
    the previous regular clause and not to the preamble."""
    blocks = [
        _ep("p_0001", "1. Предмет", "1.", 0),
        _ep("p_0002", "Приложение № 1", None, None),
        _ep("p_0003", "Вступительный текст приложения", None, None),
        _ep("p_0004", "1. Перечень оборудования", "1.", 0),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    by_label = {c.label: c for c in clauses}
    annex_header = by_label["Приложение № 1"]
    assert [p.block_id for p in annex_header.paragraphs] == ["p_0002", "p_0003"]
    # The previous regular clause did NOT pick up the annex-prelude paragraph.
    assert [p.block_id for p in by_label["1."].paragraphs] == ["p_0001"]


def test_annex_table_attaches_to_current_annex_clause():
    """A table that appears between two paragraphs of an annex clause
    attaches to that annex clause; a table that appears before the first
    numbered annex clause attaches to the annex header."""
    blocks = [
        _ep("p_0001", "Приложение № 1", None, None),
        _table("t_0001", block_index=1),
        _ep("p_0002", "1. Перечень оборудования", "1.", 0),
        _table("t_0002", block_index=3),
        _ep("p_0003", "Продолжение пункта 1", None, None),
    ]
    clauses = ClauseSegmenter().segment(blocks)
    by_label = {c.label: c for c in clauses}
    # No standalone-table clause was emitted.
    assert not any("STANDALONE_TABLE" in c.flags for c in clauses)
    # The table before the first annex clause hangs off the annex header.
    assert [t.block_id for t in by_label["Приложение № 1"].tables] == ["t_0001"]
    # The table inside the annex clause hangs off that clause.
    assert [t.block_id for t in by_label["Приложение № 1, п. 1"].tables] == ["t_0002"]
```

- [ ] **Step 2: Run the test, expect failure**

Run: `cd backend && pytest tests/processing/test_clause_segmenter.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `backend/app/processing/clause_segmenter.py`**

```python
from __future__ import annotations
import re
from typing import Sequence, Union

from app.processing.types import Clause, EnrichedParagraph, RawTable

Block = Union[EnrichedParagraph, RawTable]

# A paragraph whose text matches this pattern marks the start of the
# requisites/signatures section. Common Russian-contract variants include
# "Реквизиты сторон", "Подписи сторон", "Подписи и реквизиты сторон",
# "Адреса и реквизиты сторон", and a bare "Реквизиты". Once entered, the
# section runs to the end of the document — every subsequent block
# (paragraphs and tables) plus the matched heading paragraph itself are
# attached to the requisites clause.
_REQUISITES_RE = re.compile(
    r"^(?:"
    r"реквизиты\s+сторон"                       # "Реквизиты сторон"
    r"|подписи\s+сторон"                         # "Подписи сторон"
    r"|подписи\s+и\s+реквизиты(?:\s+сторон)?"    # "Подписи и реквизиты [сторон]"
    r"|адреса\s+и\s+реквизиты(?:\s+сторон)?"     # "Адреса и реквизиты [сторон]"
    r"|реквизиты"                                # bare "Реквизиты"
    r")\s*$",
    re.IGNORECASE,
)
# Section marker for an annex / appendix. When matched, opens a new annex
# label that prefixes subsequent numbered clauses (e.g. "Приложение № 1, п. 2").
# A new annex match resets the prefix to the new annex name.
_ANNEX_RE = re.compile(r"^\s*приложение\s*[№#]?\s*\d+", re.IGNORECASE)


class ClauseSegmenter:
    def segment(self, blocks: Sequence[Block]) -> list[Clause]:
        """Segment paragraphs into clauses; tables attach to the current clause.

        A `RawTable` that appears while a clause is open is appended to that
        clause's `tables` list. A `RawTable` that appears with no open clause
        (before any numbered clause and not inside the preamble of paragraphs)
        produces a standalone `Clause` with label="Таблица" and the
        STANDALONE_TABLE flag (manual review required).

        Once a paragraph matching "Реквизиты сторон" is seen, every later
        block (paragraph or table) is attached to that requisites clause —
        the requisites section is always the final section of a Russian
        contract, so it absorbs everything to end-of-document.

        Picking the right heading: the segmenter does a tail-window pre-scan
        over the **last 30 top-level paragraphs** (or all paragraphs if the
        document has fewer than 30) and records `last_requisites_idx` — the
        index in the original `blocks` list of the **FIRST** paragraph in that
        tail window whose stripped text matches `_REQUISITES_RE`. The tail
        gate prevents a mid-document heading from accidentally activating
        requisites mode in long documents, while still letting small
        documents (where requisites can sit at any position) work. We pick
        the FIRST match inside the tail window because once we enter
        requisites mode we never exit — a later "Подписи сторон" heading
        following an earlier "Реквизиты сторон" heading should be absorbed
        into the same single requisites clause, not start a new one.

        In the main loop, requisites mode is triggered only when
        `current_block_index == last_requisites_idx`. Mid-document phrases
        such as "В случае изменения реквизитов стороны" do not match
        `_REQUISITES_RE` (it is anchored with `^…$`), so for documents
        without a real requisites heading `last_requisites_idx` stays
        `None` and requisites mode never activates.

        Annexes ("Приложение № N"): a paragraph matching `_ANNEX_RE` opens a
        new annex section. The annex heading itself becomes a top-level
        clause (`current_annex_clause`). While an annex is active, every
        numbered clause inside it is created with `parent_key` pointing at
        the annex header (so the document tree preserves the annex
        grouping) and its label is prefixed with the annex name (e.g.
        "Приложение № 1, п. 2"). Continuation blocks (unnumbered paragraphs
        and tables) inside an annex follow the regular rule: if a numbered
        annex clause is currently open they attach to it; otherwise they
        attach to the annex header. A subsequent `_ANNEX_RE` match closes
        the previous annex and opens a new one. Entering requisites mode
        ends all annexes (requisites always come last in a Russian
        contract).
        """
        clauses: list[Clause] = []
        stack: list[Clause] = []
        preamble: Clause | None = None
        current_requisites_clause: Clause | None = None
        current_annex_clause: Clause | None = None
        current_annex_label: str | None = None
        # Tail-window pre-scan: look only in the last 30 top-level paragraphs
        # (or all paragraphs if the document has fewer). Pick the FIRST
        # paragraph in that window whose stripped text matches
        # `_REQUISITES_RE` and record its index in the original `blocks`
        # list. None if no paragraph in the window matches.
        last_requisites_idx: int | None = None
        all_paras = [b for b in blocks if isinstance(b, EnrichedParagraph)]
        window = all_paras[-30:] if len(all_paras) >= 30 else all_paras
        for p in window:
            if _REQUISITES_RE.match(p.text_runs.strip()):
                last_requisites_idx = blocks.index(p)
                break
        for current_block_index, b in enumerate(blocks):
            # Once inside the requisites section, every block (paragraph or
            # table) is appended to the requisites clause regardless of type.
            if current_requisites_clause is not None:
                if isinstance(b, RawTable):
                    current_requisites_clause.tables.append(b)
                else:
                    current_requisites_clause.paragraphs.append(b)
                continue
            if isinstance(b, RawTable):
                if stack:
                    stack[-1].tables.append(b)
                elif current_annex_clause is not None:
                    # Inside an annex but no numbered annex clause open yet
                    # — attach to the annex header.
                    current_annex_clause.tables.append(b)
                elif preamble is not None:
                    preamble.tables.append(b)
                else:
                    sc = Clause(
                        clause_key=f"c_{b.block_id}",
                        label="Таблица",
                        level=0,
                        parent_key=None,
                    )
                    sc.tables.append(b)
                    sc.flags.add("STANDALONE_TABLE")
                    clauses.append(sc)
                continue
            p = b
            if current_block_index == last_requisites_idx:
                # Requisites mode begins. Any active annex is terminated —
                # requisites always come last in a Russian contract.
                stack.clear()
                current_annex_clause = None
                current_annex_label = None
                current_requisites_clause = Clause(
                    clause_key=f"c_{p.block_id}",
                    label="Реквизиты сторон",
                    level=0,
                    parent_key=None,
                )
                # The matched heading paragraph itself is the first block of
                # the requisites clause.
                current_requisites_clause.paragraphs.append(p)
                clauses.append(current_requisites_clause)
                continue
            # Annex section heading ("Приложение № N"). Open a new annex
            # clause and switch the active prefix; subsequent numbered
            # clauses will be relabelled with this prefix and parented at
            # this annex header.
            annex_match = _ANNEX_RE.match(p.text_runs.strip())
            if annex_match:
                stack.clear()
                current_annex_label = p.text_runs.strip()
                current_annex_clause = Clause(
                    clause_key=f"c_{p.block_id}",
                    label=current_annex_label,
                    level=0,
                    parent_key=None,
                )
                current_annex_clause.paragraphs.append(p)
                clauses.append(current_annex_clause)
                continue
            level = self._level_of(p)
            if level is None:
                if stack:
                    stack[-1].paragraphs.append(p)
                    if len(stack[-1].paragraphs) > 1:
                        stack[-1].flags.add("MULTI_PARAGRAPH")
                elif current_annex_clause is not None:
                    # Between the annex header and the first numbered annex
                    # clause: attach to the annex header rather than letting
                    # the paragraph fall through to the preamble or the
                    # previous regular clause.
                    current_annex_clause.paragraphs.append(p)
                    if len(current_annex_clause.paragraphs) > 1:
                        current_annex_clause.flags.add("MULTI_PARAGRAPH")
                else:
                    if preamble is None:
                        preamble = Clause(
                            clause_key=f"c_{p.block_id}",
                            label="Преамбула",
                            level=0,
                            parent_key=None,
                        )
                        clauses.append(preamble)
                    preamble.paragraphs.append(p)
                continue
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                parent_key = stack[-1].clause_key
            elif current_annex_clause is not None and current_annex_label is not None:
                # First numbered clause inside an annex — parent it to the
                # annex header so the document tree preserves the grouping.
                parent_key = current_annex_clause.clause_key
            else:
                parent_key = None
            base_label = p.rendered_number or p.text_runs[:32]
            if current_annex_label is not None and p.rendered_number:
                # Strip a single trailing "." from the rendered number for
                # readability ("1." → "п. 1") then prefix with the annex.
                num = p.rendered_number.rstrip(".")
                full_label = f"{current_annex_label}, п. {num}"
            else:
                full_label = base_label
            new_clause = Clause(
                clause_key=f"c_{p.block_id}",
                label=full_label,
                level=level,
                parent_key=parent_key,
            )
            new_clause.paragraphs.append(p)
            clauses.append(new_clause)
            stack.append(new_clause)
        for c in clauses:
            if len(c.paragraphs) > 1:
                c.flags.add("MULTI_PARAGRAPH")
        return clauses

    def _level_of(self, p: EnrichedParagraph) -> int | None:
        if p.num_id is not None and p.ilvl is not None:
            return p.ilvl
        if p.rendered_number:
            return len(p.rendered_number.rstrip(".").split(".")) - 1
        return None
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd backend && pytest tests/processing/test_clause_segmenter.py -v`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/processing/clause_segmenter.py backend/tests/processing/test_clause_segmenter.py
git commit -m "feat(processing): add ClauseSegmenter (state-machine with parent links)"
```

---

## Task 5: ChangedClauseDetector

**Files:**
- Create: `backend/app/processing/changed_clause_detector.py`
- Test: `backend/tests/processing/test_changed_clause_detector.py`

- [ ] **Step 1: Write the failing test**

```python
from app.processing.types import Clause, EnrichedParagraph, RevisionRecord
from app.processing.changed_clause_detector import ChangedClauseDetector


def _ep_with_rev(block_id: str, text: str, accepted: str, rev_type: str) -> EnrichedParagraph:
    return EnrichedParagraph(
        block_id=block_id,
        text_runs=accepted,
        num_id=1,
        ilvl=0,
        original_text=text,
        accepted_text=accepted,
        revisions=(RevisionRecord(type=rev_type, text=accepted if rev_type == "INS" else text),),
        rendered_number="1.",
        numbering_confidence=1.0,
    )


def _clause_with(paragraphs):
    c = Clause(clause_key="c_p_0001", label="1.", level=0, parent_key=None)
    c.paragraphs.extend(paragraphs)
    return c


def test_detects_clause_with_textual_revision():
    p = _ep_with_rev("p_0001", "old", "new", "INS")
    clauses = [_clause_with([p])]
    changed = ChangedClauseDetector().detect(clauses)
    assert len(changed) == 1


def test_skips_clause_with_only_format_only_revisions():
    p = EnrichedParagraph(
        block_id="p_0001", text_runs="x", num_id=1, ilvl=0,
        original_text="x", accepted_text="x",
        revisions=(RevisionRecord(type="FORMAT_ONLY", text=""),),
        rendered_number="1.", numbering_confidence=1.0,
    )
    clauses = [_clause_with([p])]
    assert ChangedClauseDetector().detect(clauses) == []


def test_marks_new_clause_when_all_paragraphs_are_inserts():
    p = _ep_with_rev("p_0001", "", "Новый текст", "INS")
    clauses = [_clause_with([p])]
    changed = ChangedClauseDetector().detect(clauses)
    assert "NEW_CLAUSE" in changed[0].flags


def test_marks_deleted_clause_when_all_paragraphs_are_deletes():
    p = _ep_with_rev("p_0001", "Старый текст", "", "DEL")
    clauses = [_clause_with([p])]
    changed = ChangedClauseDetector().detect(clauses)
    assert "DELETED_CLAUSE" in changed[0].flags


def test_includes_clause_with_table_revisions_even_without_paragraph_revisions():
    """A clause whose paragraph has no revisions but contains a table with
    has_revisions=True must still be reported as changed."""
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    p = EnrichedParagraph(
        block_id="p_0001", text_runs="Шапка", num_id=1, ilvl=0,
        original_text="Шапка", accepted_text="Шапка",
        revisions=(),
        rendered_number="1.", numbering_confidence=1.0,
    )
    cell = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="X"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=1,
        rows=(RawTableRow(cells=(cell,)),), has_revisions=True,
    )
    clause = _clause_with([p])
    clause.tables.append(table)
    changed = ChangedClauseDetector().detect([clause])
    assert len(changed) == 1


def test_skips_clause_with_table_having_no_revisions():
    """A clause with a table that has no revisions and no paragraph revisions
    is not reported as changed (and a STANDALONE_TABLE without revisions is
    also skipped — only STANDALONE_TABLE flag forces inclusion)."""
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    p = EnrichedParagraph(
        block_id="p_0001", text_runs="Шапка", num_id=1, ilvl=0,
        original_text="Шапка", accepted_text="Шапка",
        revisions=(),
        rendered_number="1.", numbering_confidence=1.0,
    )
    cell = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="X"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=1,
        rows=(RawTableRow(cells=(cell,)),), has_revisions=False,
    )
    clause = _clause_with([p])
    clause.tables.append(table)
    assert ChangedClauseDetector().detect([clause]) == []


def test_includes_standalone_table_clause_even_without_revisions():
    """A clause flagged STANDALONE_TABLE is always surfaced for manual review."""
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    cell = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="X"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=0,
        rows=(RawTableRow(cells=(cell,)),), has_revisions=False,
    )
    clause = Clause(clause_key="c_t_0001", label="Таблица", level=0, parent_key=None)
    clause.tables.append(table)
    clause.flags.add("STANDALONE_TABLE")
    changed = ChangedClauseDetector().detect([clause])
    assert len(changed) == 1
```

- [ ] **Step 2: Run the test, expect failure**

Run: `cd backend && pytest tests/processing/test_changed_clause_detector.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `backend/app/processing/changed_clause_detector.py`**

```python
from __future__ import annotations
from app.processing.types import Clause


class ChangedClauseDetector:
    def detect(self, clauses: list[Clause]) -> list[Clause]:
        out: list[Clause] = []
        for c in clauses:
            textual = [
                r for p in c.paragraphs for r in p.revisions if r.type in ("INS", "DEL")
            ]
            has_table_revisions = any(t.has_revisions for t in c.tables)
            is_standalone_table = "STANDALONE_TABLE" in c.flags
            if not (textual or has_table_revisions or is_standalone_table):
                continue
            # NEW/DELETED flags only apply to paragraph-driven clauses, and
            # only if there are textual paragraph revisions to classify.
            if textual and c.paragraphs:
                if all(p.original_text.strip() == "" for p in c.paragraphs) and all(
                    r.type == "INS" for p in c.paragraphs for r in p.revisions if r.type in ("INS", "DEL")
                ):
                    c.flags.add("NEW_CLAUSE")
                if all(p.accepted_text.strip() == "" for p in c.paragraphs) and all(
                    r.type == "DEL" for p in c.paragraphs for r in p.revisions if r.type in ("INS", "DEL")
                ):
                    c.flags.add("DELETED_CLAUSE")
            out.append(c)
        return out
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd backend && pytest tests/processing/test_changed_clause_detector.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/processing/changed_clause_detector.py backend/tests/processing/test_changed_clause_detector.py
git commit -m "feat(processing): add ChangedClauseDetector with NEW/DELETED flags"
```

---

## Task 6: PartyExtractor

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/party_extractor.py`
- Test: `backend/tests/services/__init__.py`
- Test: `backend/tests/services/test_party_extractor.py`

- [ ] **Step 1: Create `backend/app/services/__init__.py`** and `backend/tests/services/__init__.py` (both empty)

```python
```

- [ ] **Step 2: Write the failing test**

```python
from app.services.party_extractor import PartyExtractor, ExtractedParty


def test_extracts_two_parties_with_role_labels():
    preamble = (
        'ООО "Ромашка", в лице директора Иванова И.И., именуемое в дальнейшем "Арендодатель", '
        'и АО "Василёк", в лице Петрова П.П., именуемое в дальнейшем "Арендатор", '
        'заключили настоящий договор'
    )
    parties = PartyExtractor().extract(preamble)
    assert len(parties) == 2
    by_role = {p.role: p for p in parties}
    assert "Арендодатель" in by_role
    assert "Арендатор" in by_role
    assert "Ромашка" in by_role["Арендодатель"].name
    assert "Василёк" in by_role["Арендатор"].name


def test_handles_far_form_dalee():
    preamble = (
        'ИП Сидоров А.А. (далее — Исполнитель) и ПАО "СберТех" (далее — Заказчик)'
    )
    parties = PartyExtractor().extract(preamble)
    roles = sorted(p.role for p in parties)
    assert roles == ["Заказчик", "Исполнитель"]


def test_returns_empty_for_text_without_parties():
    assert PartyExtractor().extract("Никаких сторон тут нет") == []
```

- [ ] **Step 3: Run the test, expect failure**

Run: `cd backend && pytest tests/services/test_party_extractor.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 4: Implement `backend/app/services/party_extractor.py`**

```python
from __future__ import annotations
import re
from dataclasses import dataclass

ENTITY_PREFIX = r"(?:ООО|АО|ПАО|ЗАО|ИП|ОАО|НКО|АНО|ФГУП|ГУП)"
NAME_QUOTED = r'"[^"]+"'
NAME_UNQUOTED = r"[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.[А-ЯЁ]\.)?"
NAME_PATTERN = rf"(?:{NAME_QUOTED}|{NAME_UNQUOTED})"
ENTITY = rf"{ENTITY_PREFIX}\s+{NAME_PATTERN}"
ROLE_QUOTED = r'"([^"]+)"'

PATTERN_DALEE_QUOTED = re.compile(
    rf"({ENTITY})[^.]*?(?:именуем(?:ое|ый|ая)\s+в\s+дальнейшем)\s+{ROLE_QUOTED}",
    re.IGNORECASE,
)
PATTERN_DALEE_DASH = re.compile(
    rf"({ENTITY})[^.]*?\(\s*далее\s*[—-]\s*([А-ЯЁ][а-яё]+)\s*\)",
    re.IGNORECASE,
)


@dataclass
class ExtractedParty:
    name: str
    role: str
    confidence: float


class PartyExtractor:
    def extract(self, preamble_text: str) -> list[ExtractedParty]:
        seen: dict[str, ExtractedParty] = {}
        for m in PATTERN_DALEE_QUOTED.finditer(preamble_text):
            name = m.group(1).strip()
            role = m.group(2).strip()
            seen[role] = ExtractedParty(name=name, role=role, confidence=0.9)
        for m in PATTERN_DALEE_DASH.finditer(preamble_text):
            name = m.group(1).strip()
            role = m.group(2).strip()
            seen.setdefault(role, ExtractedParty(name=name, role=role, confidence=0.85))
        return list(seen.values())
```

- [ ] **Step 5: Run the test, expect pass**

Run: `cd backend && pytest tests/services/test_party_extractor.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/party_extractor.py backend/tests/services/test_party_extractor.py backend/app/services/__init__.py backend/tests/services/__init__.py
git commit -m "feat(services): add regex-based PartyExtractor for Russian preambles"
```

---

## Task 7: ProtocolRowBuilder

**Files:**
- Create: `backend/app/services/protocol_generator.py`
- Test: `backend/tests/services/test_protocol_generator.py`

- [ ] **Step 1: Write the failing test**

```python
from app.processing.types import EnrichedParagraph, Clause, RevisionRecord
from app.services.protocol_generator import ProtocolRowBuilder, BuildContext, BuiltRow


def _make_clause(label, original, accepted, flags=None, rev_type="INS"):
    p = EnrichedParagraph(
        block_id="p_0001", text_runs=accepted or original,
        num_id=1, ilvl=0,
        original_text=original, accepted_text=accepted,
        revisions=(RevisionRecord(type=rev_type, text=accepted or original),),
        rendered_number=label, numbering_confidence=1.0,
    )
    c = Clause(clause_key="c_p_0001", label=label, level=0, parent_key=None)
    c.paragraphs.append(p)
    if flags:
        c.flags.update(flags)
    return c


def test_basic_row_maps_columns():
    clause = _make_clause("1.", "Старый текст", "Новый текст")
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([clause], ctx)
    assert len(rows) == 1
    r = rows[0]
    assert r.point_label == "1."
    assert r.party_1_text == "Старый текст"   # counterparty column = original
    assert r.party_2_text == "Новый текст"    # drafting column = accepted
    assert r.agreed_text == "Редакция Арендатора"


def test_new_clause_uses_dash_in_counterparty_and_label_with_counter():
    clause = _make_clause("1.", "", "Совсем новый пункт", flags={"NEW_CLAUSE"}, rev_type="INS")
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([clause], ctx)
    assert rows[0].party_1_text == "—"
    assert rows[0].party_2_text == "Совсем новый пункт"
    assert rows[0].point_label == "Новый пункт 1"


def test_deleted_clause_uses_exclude_in_drafting():
    clause = _make_clause("3.5.", "Старый текст пункта", "", flags={"DELETED_CLAUSE"}, rev_type="DEL")
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([clause], ctx)
    assert rows[0].party_1_text == "Старый текст пункта"
    assert rows[0].party_2_text == "Исключить пункт 3.5."
    assert rows[0].point_label == "3.5."


def test_empty_role_falls_back_to_storona_2():
    clause = _make_clause("1.", "old", "new")
    ctx = BuildContext(drafting_party_role="", counterparty_role="")
    rows = ProtocolRowBuilder().build([clause], ctx)
    assert rows[0].agreed_text == "Редакция Стороны 2"


def test_clause_with_table_emits_table_cell_change_flag_and_renders_cells():
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    clause = _make_clause("1.", "Старый", "Новый")
    cellA = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="A1"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    cellB = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0002", runs=(Run(text="B1"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=2,
        rows=(RawTableRow(cells=(cellA, cellB)),), has_revisions=True,
    )
    clause.tables.append(table)
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([clause], ctx)
    assert "TABLE_CELL_CHANGE" in rows[0].flags
    # The plain-text rendering of the table cells appears in the row text.
    assert "A1" in rows[0].party_2_text
    assert "B1" in rows[0].party_2_text


def test_clause_with_unrevised_table_does_not_emit_table_cell_change_flag():
    """A table without revisions still renders into row text but does not
    trigger the TABLE_CELL_CHANGE manual-review flag."""
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    clause = _make_clause("1.", "Старый", "Новый")
    cell = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="Z1"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=2,
        rows=(RawTableRow(cells=(cell,)),), has_revisions=False,
    )
    clause.tables.append(table)
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([clause], ctx)
    assert "TABLE_CELL_CHANGE" not in rows[0].flags
    # Cell text is still rendered into the row.
    assert "Z1" in rows[0].party_2_text


def test_standalone_table_clause_without_revisions_has_no_table_cell_change():
    """A standalone table with no revisions gets STANDALONE_TABLE +
    manual_review but NOT TABLE_CELL_CHANGE — same has_revisions gate as
    regular clauses with attached tables."""
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    cell = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="X"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=0,
        rows=(RawTableRow(cells=(cell,)),), has_revisions=False,
    )
    standalone = Clause(clause_key="c_t_0001", label="Таблица", level=0, parent_key=None)
    standalone.tables.append(table)
    standalone.flags.add("STANDALONE_TABLE")
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([standalone], ctx)
    assert len(rows) == 1
    assert rows[0].point_label == "Таблица"
    assert "STANDALONE_TABLE" in rows[0].flags
    assert "manual_review" in rows[0].flags
    assert "TABLE_CELL_CHANGE" not in rows[0].flags


def test_standalone_table_clause_with_revisions_gets_table_cell_change():
    """A standalone table with revisions gets STANDALONE_TABLE +
    TABLE_CELL_CHANGE + manual_review."""
    from app.processing.types import RawTable, RawTableRow, RawTableCell, RawParagraph, Run
    cell = RawTableCell(paragraphs=(RawParagraph(
        block_id="t_0001_p_0001", runs=(Run(text="X"),),
        num_id=None, ilvl=None, style_id=None, is_in_table=True),))
    table = RawTable(
        block_id="t_0001", block_index=0,
        rows=(RawTableRow(cells=(cell,)),), has_revisions=True,
    )
    standalone = Clause(clause_key="c_t_0001", label="Таблица", level=0, parent_key=None)
    standalone.tables.append(table)
    standalone.flags.add("STANDALONE_TABLE")
    ctx = BuildContext(drafting_party_role="Арендатор", counterparty_role="Арендодатель")
    rows = ProtocolRowBuilder().build([standalone], ctx)
    assert len(rows) == 1
    assert rows[0].point_label == "Таблица"
    assert "STANDALONE_TABLE" in rows[0].flags
    assert "TABLE_CELL_CHANGE" in rows[0].flags
    assert "manual_review" in rows[0].flags
```

- [ ] **Step 2: Run the test, expect failure**

Run: `cd backend && pytest tests/services/test_protocol_generator.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `backend/app/services/protocol_generator.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field

from app.processing.types import Clause


@dataclass
class BuildContext:
    drafting_party_role: str
    counterparty_role: str


@dataclass
class BuiltRow:
    point_label: str
    party_1_text: str
    party_2_text: str
    agreed_text: str
    source_clause_key: str | None
    confidence: float
    flags: list[str] = field(default_factory=list)
    # Populated by Task 12 after the row is persisted, so row-level
    # ValidationWarnings (e.g. TABLE_CELL_CHANGE) can carry the DB id.
    # `None` for freshly built, not-yet-persisted rows.
    row_id: str | None = None


_GENITIVE_RULES = {
    "Арендатор": "Арендатора",
    "Арендодатель": "Арендодателя",
    "Заказчик": "Заказчика",
    "Исполнитель": "Исполнителя",
    "Поставщик": "Поставщика",
    "Покупатель": "Покупателя",
    "Подрядчик": "Подрядчика",
}


def _genitive(role: str) -> str:
    # Lightweight Russian noun rule for the few common roles. Fallback returns role unchanged.
    return _GENITIVE_RULES.get(role, role)


def agreed_text_for_party(role: str) -> str:
    """Return the auto-generated `agreed_text` label for a drafting role.

    Public helper used by both `ProtocolRowBuilder` and the API layer
    (e.g. the `swap-parties` handler) so the API does not reach into a
    private builder method.
    """
    role = (role or "").strip()
    if not role:
        return "Редакция Стороны 2"
    return f"Редакция {_genitive(role)}"


class ProtocolRowBuilder:
    def build(self, clauses: list[Clause], ctx: BuildContext) -> list[BuiltRow]:
        rows: list[BuiltRow] = []
        new_clause_counter = 0
        agreed = agreed_text_for_party(ctx.drafting_party_role)
        for clause in clauses:
            # Standalone table clause: emit a manual-review row.
            if "STANDALONE_TABLE" in clause.flags:
                table_text = self._render_tables(clause)
                # Mirror the regular-clause rule: only flag TABLE_CELL_CHANGE
                # when at least one attached RawTable has has_revisions=True.
                # A standalone table without revisions still gets the
                # manual_review flag (because of STANDALONE_TABLE) but no
                # TABLE_CELL_CHANGE.
                base_flags = {*clause.flags, "manual_review"}
                if any(t.has_revisions for t in clause.tables):
                    base_flags.add("TABLE_CELL_CHANGE")
                row_flags = sorted(base_flags)
                rows.append(BuiltRow(
                    point_label="Таблица",
                    party_1_text=table_text,
                    party_2_text=table_text,
                    agreed_text=agreed,
                    source_clause_key=clause.clause_key,
                    confidence=0.5,
                    flags=row_flags,
                ))
                continue
            original = "\n".join(p.original_text for p in clause.paragraphs)
            accepted = "\n".join(p.accepted_text for p in clause.paragraphs)
            flag_set = set(clause.flags)
            if clause.tables:
                # Only flag TABLE_CELL_CHANGE when at least one attached
                # RawTable has has_revisions=True. Tables without revisions
                # are rendered into the row text but do not trigger the
                # manual-review flag.
                if any(t.has_revisions for t in clause.tables):
                    flag_set.add("TABLE_CELL_CHANGE")
                table_text = self._render_tables(clause)
                if table_text:
                    if original:
                        original = f"{original}\n{table_text}"
                    else:
                        original = table_text
                    if accepted:
                        accepted = f"{accepted}\n{table_text}"
                    else:
                        accepted = table_text
            flags = sorted(flag_set)
            if "NEW_CLAUSE" in clause.flags:
                new_clause_counter += 1
                rows.append(BuiltRow(
                    point_label=f"Новый пункт {new_clause_counter}",
                    party_1_text="—",
                    party_2_text=accepted,
                    agreed_text=agreed,
                    source_clause_key=clause.clause_key,
                    confidence=self._confidence(clause),
                    flags=flags,
                ))
                continue
            if "DELETED_CLAUSE" in clause.flags:
                rows.append(BuiltRow(
                    point_label=clause.label,
                    party_1_text=original,
                    party_2_text=f"Исключить пункт {clause.label}",
                    agreed_text=agreed,
                    source_clause_key=clause.clause_key,
                    confidence=self._confidence(clause),
                    flags=flags,
                ))
                continue
            rows.append(BuiltRow(
                point_label=clause.label,
                party_1_text=original,
                party_2_text=accepted,
                agreed_text=agreed,
                source_clause_key=clause.clause_key,
                confidence=self._confidence(clause),
                flags=flags,
            ))
        return rows

    def _render_tables(self, clause: Clause) -> str:
        """Plain-text rendering of all tables attached to a clause."""
        parts: list[str] = []
        for t in clause.tables:
            for row in t.rows:
                cells = [c.text() for c in row.cells]
                parts.append(" | ".join(cells))
        return "\n".join(parts)

    def _confidence(self, clause: Clause) -> float:
        if "MULTI_PARAGRAPH" in clause.flags:
            return 0.7
        if "LOW_NUMBERING_CONFIDENCE" in clause.flags:
            return 0.6
        return 0.95
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd backend && pytest tests/services/test_protocol_generator.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/protocol_generator.py backend/tests/services/test_protocol_generator.py
git commit -m "feat(services): add ProtocolRowBuilder with NEW/DELETED clause handling"
```

---

## Task 8: ValidationEngine

**Files:**
- Create: `backend/app/processing/validation_engine.py`
- Test: `backend/tests/processing/test_validation_engine.py`

- [ ] **Step 1: Write the failing test**

```python
from app.processing.types import EnrichedParagraph, Clause, RevisionRecord, ResolverDiagnostic
from app.processing.validation_engine import ValidationEngine
from app.services.protocol_generator import BuiltRow


def _ep(rev_types: list[str], num_conf: float = 1.0) -> EnrichedParagraph:
    return EnrichedParagraph(
        block_id="p_0001", text_runs="x", num_id=1, ilvl=0,
        original_text="x", accepted_text="x",
        revisions=tuple(RevisionRecord(type=t, text="x") for t in rev_types),
        rendered_number="1.", numbering_confidence=num_conf,
    )


def _clause(p, flags=None):
    c = Clause(clause_key="c_p_0001", label="1.", level=0, parent_key=None)
    c.paragraphs.append(p)
    if flags:
        c.flags.update(flags)
    return c


def _row(point_label="1.", flags=None, confidence=0.95, row_id=None):
    return BuiltRow(
        point_label=point_label, party_1_text="x", party_2_text="x", agreed_text="x",
        source_clause_key="c_p_0001", confidence=confidence,
        flags=list(flags or []),
        row_id=row_id,
    )


def test_counts_textual_and_format_revisions():
    p = _ep(["INS", "DEL", "FORMAT_ONLY"])
    rep = ValidationEngine().validate([_row()], [_clause(p)], [])
    assert rep.textual_revisions_total == 2
    assert rep.format_only_revisions == 1


def test_empty_protocol_warning_when_no_rows():
    rep = ValidationEngine().validate([], [], [])
    kinds = [w["kind"] for w in rep.warnings]
    assert "EMPTY_PROTOCOL" in kinds


def test_low_numbering_confidence_overall():
    p = _ep(["INS"], num_conf=0.0)
    rep = ValidationEngine().validate([_row()], [_clause(p)], [])
    kinds = [w["kind"] for w in rep.warnings]
    assert "LOW_NUMBERING_CONFIDENCE_OVERALL" in kinds


def test_multi_paragraph_clause_emits_warning():
    p1 = _ep(["INS"]); p2 = _ep([])
    c = _clause(p1, flags={"MULTI_PARAGRAPH"}); c.paragraphs.append(p2)
    rep = ValidationEngine().validate([_row(confidence=0.7)], [c], [])
    kinds = [w["kind"] for w in rep.warnings]
    assert "MULTI_PARAGRAPH" in kinds


def test_unknown_numid_diagnostic_produces_numbering_mismatch_warning():
    """A `ResolverDiagnostic` with code="UNKNOWN_NUMID" from the numbering
    resolver becomes a NUMBERING_MAPPING_MISMATCH warning in the report."""
    p = _ep(["INS"])
    diag = ResolverDiagnostic(
        level="warning",
        component="numbering",
        code="UNKNOWN_NUMID",
        message="numId 999 not found in numbering.xml",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    num_warnings = [w for w in rep.warnings if w["kind"] == "NUMBERING_MAPPING_MISMATCH"]
    assert len(num_warnings) == 1
    assert num_warnings[0]["scope"] == "session"


def test_low_confidence_diagnostic_produces_low_numbering_confidence_warning():
    """A `ResolverDiagnostic` with code="LOW_CONFIDENCE" becomes a
    LOW_NUMBERING_CONFIDENCE warning, not NUMBERING_MAPPING_MISMATCH."""
    p = _ep(["INS"])
    diag = ResolverDiagnostic(
        level="warning",
        component="numbering",
        code="LOW_CONFIDENCE",
        message="low confidence for paragraph p_0001 (0.70)",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    kinds = [w["kind"] for w in rep.warnings]
    assert "LOW_NUMBERING_CONFIDENCE" in kinds
    assert "NUMBERING_MAPPING_MISMATCH" not in kinds


def test_format_only_mismatch_diagnostic_does_not_produce_warning():
    """A `ResolverDiagnostic` with code="FORMAT_ONLY_MISMATCH" is expected
    behaviour (revisions exist but the accepted text equals the original);
    it must NOT surface as a REVISION_MAPPING_MISMATCH warning."""
    p = _ep(["FORMAT_ONLY"])
    diag = ResolverDiagnostic(
        level="warning",
        component="revision",
        code="FORMAT_ONLY_MISMATCH",
        message="format-only revisions detected (original==accepted)",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    kinds = [w["kind"] for w in rep.warnings]
    assert "REVISION_MAPPING_MISMATCH" not in kinds


def test_mapping_mismatch_diagnostic_produces_revision_mismatch_warning():
    """A `ResolverDiagnostic` with code="MAPPING_MISMATCH" from the
    revision resolver becomes a REVISION_MAPPING_MISMATCH warning."""
    p = _ep(["INS"])
    diag = ResolverDiagnostic(
        level="warning",
        component="revision",
        code="MAPPING_MISMATCH",
        message="rev id 42 references unknown anchor",
        block_id="p_0001",
    )
    rep = ValidationEngine().validate([_row()], [_clause(p)], [diag])
    rev_warnings = [w for w in rep.warnings if w["kind"] == "REVISION_MAPPING_MISMATCH"]
    assert len(rev_warnings) == 1
    assert rev_warnings[0]["scope"] == "session"
    assert "rev id 42" in rev_warnings[0]["message"]


def test_validate_uses_all_clauses_not_just_changed():
    """A format-only revision sitting on an unchanged clause must still be
    counted in `format_only_revisions` because the engine receives ALL
    clauses (not just the changed subset)."""
    changed_p = _ep(["INS"])
    unchanged_p = _ep(["FORMAT_ONLY"])
    rep = ValidationEngine().validate(
        [_row()],
        [_clause(changed_p), _clause(unchanged_p)],
        [],
    )
    assert rep.textual_revisions_total == 1
    assert rep.format_only_revisions == 1


def test_table_cell_change_emits_row_level_warning():
    """Each protocol row carrying the TABLE_CELL_CHANGE flag emits a
    row-level TABLE_CELL_CHANGE warning with the row_id populated, so the
    UI can link the warning back to the offending row."""
    p = _ep(["INS"])
    row = _row(point_label="3.", flags=["TABLE_CELL_CHANGE"], row_id="row_abc")
    rep = ValidationEngine().validate([row], [_clause(p)], [])
    table_warnings = [w for w in rep.warnings if w["kind"] == "TABLE_CELL_CHANGE"]
    assert len(table_warnings) == 1
    assert table_warnings[0]["scope"] == "row"
    assert table_warnings[0]["row_id"] == "row_abc"
    assert "Таблица в пункте 3." in table_warnings[0]["message"]
```

- [ ] **Step 2: Run the test, expect failure**

Run: `cd backend && pytest tests/processing/test_validation_engine.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `backend/app/processing/validation_engine.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field

from app.processing.types import Clause, ResolverDiagnostic
from app.services.protocol_generator import BuiltRow


@dataclass
class ValidationReport:
    textual_revisions_total: int
    format_only_revisions: int
    covered_revisions: int
    numbering_confidence_mean: float
    warnings: list[dict] = field(default_factory=list)


class ValidationEngine:
    def validate(
        self,
        protocol_rows: list[BuiltRow],
        all_clauses: list[Clause],
        resolver_diagnostics: list[ResolverDiagnostic],
    ) -> ValidationReport:
        """Build a ValidationReport for the protocol.

        Inputs:
        - `protocol_rows`: the rows produced by ProtocolRowBuilder for the
          current build (used for emptiness check and TABLE_CELL_CHANGE
          warnings).
        - `all_clauses`: the full list of clauses in the document (NOT just
          the `changed_clauses` subset). Counting revisions and computing
          numbering confidence over all clauses ensures format-only
          revisions on otherwise-unchanged clauses are still tallied — a
          clause whose only revision is FORMAT_ONLY does not enter
          `changed_clauses`, so passing only the changed subset would
          silently drop those revisions from `format_only_revisions`.
        - `resolver_diagnostics`: aggregated diagnostics from the revision
          and numbering resolvers. Diagnostics are routed by their `code`,
          not by their `component`, because mapping by component alone
          produces false positives (e.g. a benign FORMAT_ONLY_MISMATCH from
          the revision resolver would otherwise surface as a
          REVISION_MAPPING_MISMATCH warning). The mapping is:
            - code="UNKNOWN_NUMID"        → NUMBERING_MAPPING_MISMATCH
            - code="LOW_CONFIDENCE"       → LOW_NUMBERING_CONFIDENCE
            - code="FORMAT_ONLY_MISMATCH" → suppressed (expected behaviour)
            - code="MAPPING_MISMATCH"     → REVISION_MAPPING_MISMATCH if
                                            component=="revision",
                                            NUMBERING_MAPPING_MISMATCH if
                                            component=="numbering"
            - any other code              → passed through verbatim as
                                            kind=code, scope="session"
        """
        textual = 0
        format_only = 0
        confidences: list[float] = []
        warnings: list[dict] = []
        for c in all_clauses:
            for p in c.paragraphs:
                for r in p.revisions:
                    if r.type in ("INS", "DEL"):
                        textual += 1
                    elif r.type == "FORMAT_ONLY":
                        format_only += 1
                if p.numbering_confidence is not None:
                    confidences.append(p.numbering_confidence)
            if "MULTI_PARAGRAPH" in c.flags:
                warnings.append({"kind": "MULTI_PARAGRAPH", "scope": "clause", "clause_key": c.clause_key,
                                 "message": f"Пункт {c.label} состоит из нескольких параграфов"})
            if "LOW_NUMBERING_CONFIDENCE" in c.flags:
                warnings.append({"kind": "LOW_NUMBERING_CONFIDENCE", "scope": "clause", "clause_key": c.clause_key,
                                 "message": f"Низкая уверенность нумерации в пункте {c.label}"})
        mean = sum(confidences) / len(confidences) if confidences else 0.0
        if confidences and mean < 0.6:
            warnings.append({"kind": "LOW_NUMBERING_CONFIDENCE_OVERALL", "scope": "session",
                             "message": "Нумерация распознана с низкой уверенностью"})
        if not confidences:
            warnings.append({"kind": "LOW_NUMBERING_CONFIDENCE_OVERALL", "scope": "session",
                             "message": "Нумерация не распознана"})
        if not protocol_rows:
            warnings.append({"kind": "EMPTY_PROTOCOL", "scope": "session", "severity": "info",
                             "message": "В документе не найдено правок"})
        # Resolver diagnostics → routed by `code`. FORMAT_ONLY_MISMATCH is
        # an expected condition (revision elements present but the accepted
        # text equals the original), so it must NOT surface as a warning.
        for d in resolver_diagnostics:
            if d.code == "FORMAT_ONLY_MISMATCH":
                continue
            if d.code == "UNKNOWN_NUMID":
                kind = "NUMBERING_MAPPING_MISMATCH"
            elif d.code == "LOW_CONFIDENCE":
                kind = "LOW_NUMBERING_CONFIDENCE"
            elif d.code == "MAPPING_MISMATCH":
                kind = (
                    "NUMBERING_MAPPING_MISMATCH"
                    if d.component == "numbering"
                    else "REVISION_MAPPING_MISMATCH"
                )
            else:
                # Unknown code — pass through verbatim so future codes don't
                # need engine changes to be surfaced.
                kind = d.code
            warnings.append({
                "kind": kind,
                "scope": "session",
                "severity": d.level,
                "component": d.component,
                "code": d.code,
                "block_id": d.block_id,
                "message": d.message,
            })
        # Each protocol row with the TABLE_CELL_CHANGE flag → row-level
        # warning carrying the row_id, so the UI can link the warning back
        # to the offending row. `row_id` is populated by Task 12 after the
        # row is persisted; if absent (pre-persistence), `source_clause_key`
        # is still attached for fallback linkage.
        for row in protocol_rows:
            if "TABLE_CELL_CHANGE" in (row.flags or []):
                warnings.append({
                    "kind": "TABLE_CELL_CHANGE",
                    "scope": "row",
                    "severity": "warning",
                    "row_id": row.row_id,
                    "point_label": row.point_label,
                    "source_clause_key": row.source_clause_key,
                    "message": f"Таблица в пункте {row.point_label} требует проверки",
                })
        return ValidationReport(
            textual_revisions_total=textual,
            format_only_revisions=format_only,
            covered_revisions=textual,   # MVP: all textual revisions are mapped to rows
            numbering_confidence_mean=mean,
            warnings=warnings,
        )
```

- [ ] **Step 4: Run the test, expect pass**

Run: `cd backend && pytest tests/processing/test_validation_engine.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/processing/validation_engine.py backend/tests/processing/test_validation_engine.py
git commit -m "feat(processing): add ValidationEngine with coverage and warning checks"
```

---

## Task 9: FastAPI app + Celery wiring + storage

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/services/storage.py`
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/celery_app.py`
- Create: `backend/app/workers/tasks.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/schemas/party.py`
- Create: `backend/app/schemas/protocol.py`
- Create: `backend/app/schemas/validation.py`
- Test: `backend/tests/api/__init__.py`
- Test: `backend/tests/api/test_health.py`

- [ ] **Step 1: Create `backend/app/services/storage.py`**

```python
from __future__ import annotations
import io
import boto3
from botocore.client import Config

from app.config import get_settings


class S3Storage:
    def __init__(self) -> None:
        s = get_settings()
        self._client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint,
            aws_access_key_id=s.s3_access_key,
            aws_secret_access_key=s.s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self._bucket = s.s3_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        existing = self._client.list_buckets().get("Buckets", [])
        if not any(b["Name"] == self._bucket for b in existing):
            self._client.create_bucket(Bucket=self._bucket)

    def put(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=key)
        return obj["Body"].read()
```

- [ ] **Step 2: Create `backend/app/schemas/__init__.py`** (empty)

```python
```

- [ ] **Step 3: Create `backend/app/schemas/party.py`**

```python
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
```

- [ ] **Step 4: Create `backend/app/schemas/validation.py`**

```python
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
```

- [ ] **Step 5: Create `backend/app/schemas/document.py`**

```python
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
```

- [ ] **Step 6: Create `backend/app/schemas/protocol.py`**

```python
from uuid import UUID
from pydantic import BaseModel


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
```

- [ ] **Step 7: Create `backend/app/api/__init__.py`** (empty)

```python
```

- [ ] **Step 8: Create `backend/app/workers/__init__.py`** (empty)

```python
```

- [ ] **Step 9: Create `backend/app/workers/celery_app.py`**

```python
from celery import Celery
from app.config import get_settings

_settings = get_settings()
celery_app = Celery(
    "disprot",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.task_default_queue = "disprot"
celery_app.conf.task_track_started = True
celery_app.autodiscover_tasks(["app.workers"])
```

- [ ] **Step 10: Create `backend/app/workers/tasks.py`** (placeholder; real pipeline added in Task 10)

```python
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.ping")
def ping() -> str:
    return "pong"
```

- [ ] **Step 11: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Disagreement Protocol", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    from app.api import documents, protocols, files
    app.include_router(documents.router)
    app.include_router(protocols.router)
    app.include_router(files.router)
    return app


app = create_app()
```

- [ ] **Step 12: Create stub routers `backend/app/api/documents.py`, `backend/app/api/protocols.py`, `backend/app/api/files.py`** so the import chain in `main.py` resolves. (Real handlers added in Tasks 10–13.)

`backend/app/api/documents.py`:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/documents", tags=["documents"])
```

`backend/app/api/protocols.py`:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/protocols", tags=["protocols"])
```

`backend/app/api/files.py`:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/files", tags=["files"])
```

- [ ] **Step 13: Create `backend/tests/api/__init__.py`** (empty)

```python
```

- [ ] **Step 14: Write the failing test `backend/tests/api/test_health.py`**

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_returns_ok():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
```

- [ ] **Step 15: Run the test, expect pass after stubs are in place**

Run: `cd backend && pytest tests/api/test_health.py -v`
Expected: 1 passed.

- [ ] **Step 16: Commit**

```bash
git add backend/app/main.py backend/app/services/storage.py backend/app/workers backend/app/api backend/app/schemas backend/tests/api
git commit -m "feat(api): scaffold FastAPI app with health endpoint and Celery wiring"
```

---

## Task 10: Document upload + Celery pipeline task

**Files:**
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/workers/tasks.py`
- Create: `backend/app/services/ingestion.py`
- Test: `backend/tests/api/test_documents_upload.py`

- [ ] **Step 1: Create `backend/app/services/ingestion.py`**

```python
from __future__ import annotations
import io
import zipfile
import uuid
import re

from app.processing.ooxml_parser import OOXMLParser
from app.processing.revision_resolver import RevisionResolver
from app.processing.numbering_resolver import NumberingResolver
from app.processing.clause_segmenter import ClauseSegmenter
from app.processing.changed_clause_detector import ChangedClauseDetector
from app.processing.validation_engine import ValidationEngine
from app.processing.types import EnrichedParagraph, RawParagraph, RawTable
from app.services.party_extractor import PartyExtractor

MAX_BYTES = 25 * 1024 * 1024


class IngestError(Exception):
    def __init__(self, http_status: int, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.message = message


def validate_upload(filename: str, data: bytes) -> None:
    if not filename.lower().endswith(".docx"):
        raise IngestError(400, "Поддерживаются только файлы .docx без макросов")
    if len(data) > MAX_BYTES:
        raise IngestError(413, "Размер файла превышает 25 MB")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise IngestError(400, "Файл повреждён или не является документом Word")
    names = set(zf.namelist())
    if "word/document.xml" not in names:
        raise IngestError(400, "В архиве отсутствует word/document.xml — это не Word-документ")
    if "word/vbaProject.bin" in names:
        raise IngestError(415, "Документ содержит макросы (vbaProject.bin) — не поддерживается")


def derive_contract_name(filename: str) -> str | None:
    name = filename
    if name.lower().endswith(".docx"):
        name = name[:-5]
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = name.replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name or None


def run_pipeline(data: bytes) -> dict:
    parser = OOXMLParser()
    raw = parser.parse(data)
    revisions, revision_diags = RevisionResolver().resolve(data, raw)
    numbering, numbering_diags = NumberingResolver().resolve(data, raw)
    # Build segmenter input by interleaving EnrichedParagraph and RawTable
    # in document order (so tables attach to their surrounding clause).
    segmenter_blocks: list = []
    enriched: list[EnrichedParagraph] = []
    for b in raw.blocks:
        if isinstance(b, RawParagraph):
            rd = revisions.get(b.block_id)
            nd = numbering.get(b.block_id)
            ep = EnrichedParagraph(
                block_id=b.block_id,
                text_runs=b.text(),
                num_id=b.num_id,
                ilvl=b.ilvl,
                original_text=rd.original_text if rd else b.text(),
                accepted_text=rd.accepted_text if rd else b.text(),
                revisions=rd.revisions if rd else (),
                rendered_number=nd.rendered_number if nd else None,
                numbering_confidence=nd.confidence if nd else 0.0,
            )
            enriched.append(ep)
            segmenter_blocks.append(ep)
        elif isinstance(b, RawTable):
            segmenter_blocks.append(b)
    clauses = ClauseSegmenter().segment(segmenter_blocks)
    changed = ChangedClauseDetector().detect(clauses)
    preamble_text = ""
    for c in clauses:
        if c.label == "Преамбула":
            preamble_text = "\n".join(p.accepted_text for p in c.paragraphs)
            break
    if not preamble_text and clauses:
        preamble_text = "\n".join(p.accepted_text for p in clauses[0].paragraphs)
    parties = PartyExtractor().extract(preamble_text)
    diagnostics = [
        {"level": d.level, "component": d.component, "code": d.code,
         "message": d.message, "block_id": d.block_id}
        for d in (*revision_diags, *numbering_diags)
    ]
    return {
        "clauses": clauses,
        "changed_clauses": changed,
        "parties": parties,
        "preflight_metrics": {
            "revisions_total": sum(len([r for r in p.revisions if r.type in ("INS", "DEL")]) for c in clauses for p in c.paragraphs),
            "format_only_count": sum(len([r for r in p.revisions if r.type == "FORMAT_ONLY"]) for c in clauses for p in c.paragraphs),
            "paragraphs_with_numbering": sum(1 for c in clauses for p in c.paragraphs if p.rendered_number),
            "numbering_confidence_mean": (
                sum(p.numbering_confidence for c in clauses for p in c.paragraphs)
                / max(1, sum(1 for c in clauses for p in c.paragraphs))
            ),
        },
        "preflight_diagnostics": diagnostics,
    }
```

- [ ] **Step 2: Replace `backend/app/workers/tasks.py`** with real pipeline task

```python
from __future__ import annotations
import uuid
from datetime import datetime

from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.clause import Clause as ClauseModel
from app.services.storage import S3Storage
from app.services.ingestion import run_pipeline


@celery_app.task(name="app.workers.tasks.process_document")
def process_document(document_id: str) -> None:
    storage = S3Storage()
    db = SessionLocal()
    try:
        doc = db.get(Document, uuid.UUID(document_id))
        if doc is None:
            return
        doc.status = DocumentStatus.PARSING
        db.commit()
        try:
            data = storage.get(doc.storage_key)
            result = run_pipeline(data)
        except Exception as exc:  # noqa: BLE001
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(exc)[:2000]
            db.commit()
            return
        for idx, c in enumerate(result["clauses"]):
            db.add(ClauseModel(
                document_id=doc.id,
                clause_key=c.clause_key,
                label=c.label,
                level=c.level,
                parent_key=c.parent_key,
                sort_order=idx,
                original_text="\n".join(p.original_text for p in c.paragraphs),
                accepted_text="\n".join(p.accepted_text for p in c.paragraphs),
                flags=sorted(c.flags),
                confidence=1.0,
                revisions=[
                    {"type": r.type, "text": r.text, "author": r.author}
                    for p in c.paragraphs for r in p.revisions
                ],
                tables_json=[
                    {
                        "block_id": t.block_id,
                        "has_revisions": t.has_revisions,
                        "rows": [[cell.text() for cell in row.cells] for row in t.rows],
                    }
                    for t in c.tables
                ],
            ))
        for ep in result["parties"]:
            db.add(Party(document_id=doc.id, name=ep.name, role=ep.role, confidence=ep.confidence))
        doc.preflight_metrics = result["preflight_metrics"]
        doc.metadata_json = {"preflight_diagnostics": result["preflight_diagnostics"]}
        doc.status = DocumentStatus.PARSED
        doc.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 3: Replace `backend/app/api/documents.py`** with real upload + analysis endpoints (analysis is filled in Task 11; here we add upload)

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.schemas.document import DocumentCreated
from app.services.ingestion import IngestError, validate_upload, derive_contract_name
from app.services.storage import S3Storage
from app.workers.tasks import process_document

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentCreated, status_code=201)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> DocumentCreated:
    data = file.file.read()
    try:
        validate_upload(file.filename or "", data)
    except IngestError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message)
    doc_id = uuid.uuid4()
    storage_key = f"documents/{doc_id}/input.docx"
    S3Storage().put(storage_key, data)
    doc = Document(
        id=doc_id,
        original_filename=file.filename or "document.docx",
        storage_key=storage_key,
        contract_name=derive_contract_name(file.filename or ""),
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    process_document.delay(str(doc_id))
    return DocumentCreated(id=doc_id, status=doc.status.value)
```

- [ ] **Step 4: Write the failing test `backend/tests/api/test_documents_upload.py`**

```python
import io
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from tests.fixtures.builders import build_simple_docx


def test_upload_rejects_non_docx_extension():
    with TestClient(app) as client:
        r = client.post("/api/documents", files={"file": ("a.txt", b"hi", "text/plain")})
        assert r.status_code == 400


def test_upload_rejects_corrupted_zip():
    with TestClient(app) as client:
        r = client.post("/api/documents", files={"file": ("a.docx", b"not-a-zip", "application/octet-stream")})
        assert r.status_code == 400


def test_upload_happy_path_creates_document(monkeypatch):
    data = build_simple_docx(["hello"])
    captured = {}
    class _FakeStorage:
        def __init__(self): captured["init"] = True
        def put(self, k, b): captured["key"] = k; captured["len"] = len(b)
    class _FakeTask:
        def delay(self, doc_id): captured["task_doc_id"] = doc_id
    monkeypatch.setattr("app.api.documents.S3Storage", _FakeStorage)
    monkeypatch.setattr("app.api.documents.process_document", _FakeTask())
    with TestClient(app) as client:
        r = client.post("/api/documents", files={"file": ("contract.docx", data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "uploaded"
        assert "id" in body
        assert captured["task_doc_id"] == body["id"]
```

> **Test setup note:** these API tests require a working PostgreSQL connection (Docker Compose up + `alembic upgrade head`). The Celery side is mocked via `monkeypatch`, so no broker is needed.

- [ ] **Step 5: Run the test, expect pass**

Run: `cd backend && pytest tests/api/test_documents_upload.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ingestion.py backend/app/workers/tasks.py backend/app/api/documents.py backend/tests/api/test_documents_upload.py
git commit -m "feat(api): add document upload endpoint and Celery pipeline task"
```

---

## Task 11: Analysis endpoint + party confirmation

**Files:**
- Modify: `backend/app/api/documents.py` (add GET analysis, PATCH parties)
- Test: `backend/tests/api/test_documents_analysis.py`

- [ ] **Step 1: Append the new endpoints to `backend/app/api/documents.py`**

Append after the existing `upload_document` function:

```python
from app.models.party import Party
from app.schemas.document import AnalysisOut, PreflightDiagnostic, PreflightMetrics
from app.schemas.party import PartiesUpdateIn, PartyOut
from app.schemas.validation import ValidationReportOut


@router.get("/{document_id}/analysis", response_model=AnalysisOut)
def get_analysis(document_id: uuid.UUID, db: Session = Depends(get_db)) -> AnalysisOut:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    parties = db.query(Party).filter(Party.document_id == document_id).all()
    diags_raw = ((doc.metadata_json or {}).get("preflight_diagnostics") or [])
    return AnalysisOut(
        id=doc.id,
        status=doc.status.value,
        contract_name=doc.contract_name,
        preflight_metrics=PreflightMetrics(**doc.preflight_metrics) if doc.preflight_metrics else None,
        preflight_diagnostics=[PreflightDiagnostic(**d) for d in diags_raw],
        parties=[PartyOut(id=p.id, name=p.name, role=p.role, confidence=p.confidence) for p in parties],
        validation_report=ValidationReportOut(**doc.validation_report) if doc.validation_report else None,
        drafting_party_id=doc.drafting_party_id,
    )


@router.patch("/{document_id}/parties", response_model=AnalysisOut)
def update_parties(
    document_id: uuid.UUID,
    payload: PartiesUpdateIn,
    db: Session = Depends(get_db),
) -> AnalysisOut:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    existing = {p.id: p for p in db.query(Party).filter(Party.document_id == document_id).all()}
    seen_ids: set[uuid.UUID] = set()
    for item in payload.parties:
        if item.id and item.id in existing:
            existing[item.id].name = item.name
            existing[item.id].role = item.role
            seen_ids.add(item.id)
        else:
            new_party = Party(document_id=document_id, name=item.name, role=item.role, confidence=1.0)
            db.add(new_party)
    for pid, party_obj in existing.items():
        if pid not in seen_ids:
            db.delete(party_obj)
    if payload.drafting_party_id is not None:
        doc.drafting_party_id = payload.drafting_party_id
        doc.status = DocumentStatus.PARTIES_CONFIRMED
    db.commit()
    return get_analysis(document_id, db)
```

- [ ] **Step 2: Write the failing test `backend/tests/api/test_documents_analysis.py`**

```python
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party


@pytest.fixture
def parsed_doc():
    db = SessionLocal()
    doc = Document(
        id=uuid.uuid4(),
        original_filename="t.docx",
        storage_key="t/k",
        contract_name="t",
        status=DocumentStatus.PARSED,
        preflight_metrics={
            "revisions_total": 1, "format_only_count": 0,
            "paragraphs_with_numbering": 1, "numbering_confidence_mean": 1.0,
        },
        metadata_json={"preflight_diagnostics": [
            {"level": "warning", "component": "numbering", "code": "UNKNOWN_NUMID",
             "message": "numId 999 not found in numbering.xml", "block_id": "p_0001"},
        ]},
    )
    db.add(doc)
    p = Party(document_id=doc.id, name="ООО Ромашка", role="Арендодатель", confidence=0.9)
    db.add(p)
    db.commit()
    yield doc, p
    db.delete(p); db.delete(doc); db.commit(); db.close()


def test_get_analysis_returns_parties(parsed_doc):
    doc, _ = parsed_doc
    with TestClient(app) as client:
        r = client.get(f"/api/documents/{doc.id}/analysis")
        assert r.status_code == 200
        body = r.json()
        assert body["contract_name"] == "t"
        assert len(body["parties"]) == 1
        assert body["parties"][0]["role"] == "Арендодатель"


def test_get_analysis_includes_preflight_diagnostics(parsed_doc):
    doc, _ = parsed_doc
    with TestClient(app) as client:
        r = client.get(f"/api/documents/{doc.id}/analysis")
        assert r.status_code == 200
        body = r.json()
        assert "preflight_diagnostics" in body
        assert len(body["preflight_diagnostics"]) == 1
        d = body["preflight_diagnostics"][0]
        assert d["component"] == "numbering"
        assert "numId 999" in d["message"]


def test_get_analysis_includes_validation_report_warnings(parsed_doc):
    """When the document has a stored validation_report, the analysis
    response surfaces it as `validation_report` (validation summary). In
    particular, REVISION_MAPPING_MISMATCH / NUMBERING_MAPPING_MISMATCH
    warnings produced from resolver diagnostics on the build pass should
    be visible to the frontend so the validation banner can render."""
    doc, _ = parsed_doc
    # Backfill a minimal validation_report on the fixture document.
    db = SessionLocal()
    persisted = db.get(Document, doc.id)
    persisted.validation_report = {
        "textual_revisions_total": 1,
        "format_only_revisions": 0,
        "covered_revisions": 1,
        "numbering_confidence_mean": 1.0,
        "warnings": [
            {"kind": "NUMBERING_MAPPING_MISMATCH", "scope": "session",
             "severity": "warning", "component": "numbering",
             "block_id": "p_0001",
             "message": "numId 999 not found in numbering.xml"},
        ],
    }
    db.commit(); db.close()
    with TestClient(app) as client:
        r = client.get(f"/api/documents/{doc.id}/analysis")
        assert r.status_code == 200
        body = r.json()
        assert body["validation_report"] is not None
        kinds = [w["kind"] for w in body["validation_report"]["warnings"]]
        assert "NUMBERING_MAPPING_MISMATCH" in kinds


def test_patch_parties_sets_drafting_and_status(parsed_doc):
    doc, p = parsed_doc
    with TestClient(app) as client:
        r = client.patch(f"/api/documents/{doc.id}/parties", json={
            "parties": [{"id": str(p.id), "name": "ООО Ромашка", "role": "Арендодатель"},
                        {"name": "АО Василёк", "role": "Арендатор"}],
            "drafting_party_id": str(p.id),
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["drafting_party_id"] == str(p.id)
        assert body["status"] == "parties_confirmed"
        assert len(body["parties"]) == 2
```

- [ ] **Step 3: Run the test, expect pass**

Run: `cd backend && pytest tests/api/test_documents_analysis.py -v`
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/documents.py backend/tests/api/test_documents_analysis.py
git commit -m "feat(api): add analysis GET and parties PATCH endpoints"
```

---

## Task 12: Protocol generation + row edit endpoints

**Files:**
- Modify: `backend/app/api/protocols.py`
- Test: `backend/tests/api/test_protocols.py`

- [ ] **Step 1: Replace `backend/app/api/protocols.py`** with full implementation

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.clause import Clause as ClauseModel
from app.models.protocol import Protocol, ProtocolRow
from app.processing.types import (
    EnrichedParagraph, Clause as ClauseDC, RawParagraph, RawTable, RawTableCell, RawTableRow,
    RevisionRecord, Run,
)
from app.processing.validation_engine import ValidationEngine
from app.services.protocol_generator import ProtocolRowBuilder, BuildContext, agreed_text_for_party
from app.schemas.protocol import ProtocolOut, ProtocolRowOut, ProtocolRowPatch, ProtocolRowCreate

router = APIRouter(prefix="/api", tags=["protocols"])


def _serialize_row(row: ProtocolRow) -> ProtocolRowOut:
    return ProtocolRowOut(
        id=row.id, sort_order=row.sort_order, point_label=row.point_label,
        party_1_text=row.party_1_text, party_2_text=row.party_2_text, agreed_text=row.agreed_text,
        source_clause_key=row.source_clause_key, confidence=row.confidence,
        flags=list(row.flags), user_edited=row.user_edited,
    )


@router.post("/documents/{document_id}/protocol", response_model=ProtocolOut, status_code=201)
def build_protocol(document_id: uuid.UUID, db: Session = Depends(get_db)) -> ProtocolOut:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    if doc.drafting_party_id is None:
        raise HTTPException(409, "Drafting party not set")
    parties = db.query(Party).filter(Party.document_id == document_id).all()
    if len(parties) != 2:
        raise HTTPException(409, "MVP supports exactly two parties")
    drafting = next((p for p in parties if p.id == doc.drafting_party_id), None)
    counterparty = next((p for p in parties if p.id != doc.drafting_party_id), None)
    if drafting is None or counterparty is None:
        raise HTTPException(409, "Drafting party not found")
    clause_models = (
        db.query(ClauseModel)
        .filter(ClauseModel.document_id == document_id)
        .order_by(ClauseModel.sort_order)
        .all()
    )
    clauses_dc: list[ClauseDC] = []
    for cm in clause_models:
        c = ClauseDC(clause_key=cm.clause_key, label=cm.label, level=cm.level, parent_key=cm.parent_key)
        c.flags = set(cm.flags or [])
        c.paragraphs.append(EnrichedParagraph(
            block_id=cm.clause_key,
            text_runs=cm.accepted_text,
            num_id=None, ilvl=cm.level,
            original_text=cm.original_text,
            accepted_text=cm.accepted_text,
            revisions=tuple(RevisionRecord(type=r.get("type", ""), text=r.get("text", ""), author=r.get("author", "")) for r in (cm.revisions or [])),
            rendered_number=cm.label,
            numbering_confidence=cm.confidence,
        ))
        # Rehydrate tables from tables_json so ProtocolRowBuilder can render
        # TABLE_CELL_CHANGE content. We rebuild minimal RawTable objects with
        # one cell paragraph per cell text.
        for t in (cm.tables_json or []):
            rows_dc: list[RawTableRow] = []
            for row_cells in t.get("rows", []):
                cells = tuple(
                    RawTableCell(paragraphs=(RawParagraph(
                        block_id=f"{t['block_id']}_p_{i:04d}",
                        runs=(Run(text=cell_text or ""),),
                        num_id=None, ilvl=None, style_id=None, is_in_table=True,
                    ),))
                    for i, cell_text in enumerate(row_cells)
                )
                rows_dc.append(RawTableRow(cells=cells))
            c.tables.append(RawTable(
                block_id=t["block_id"],
                block_index=0,
                rows=tuple(rows_dc),
                has_revisions=bool(t.get("has_revisions", False)),
            ))
        clauses_dc.append(c)
    changed = [
        c for c in clauses_dc
        if any(r.type in ("INS", "DEL") for p in c.paragraphs for r in p.revisions)
        or any(t.has_revisions for t in c.tables)
        or "STANDALONE_TABLE" in c.flags
    ]
    ctx = BuildContext(drafting_party_role=drafting.role, counterparty_role=counterparty.role)
    built = ProtocolRowBuilder().build(changed, ctx)
    db.query(ProtocolRow).filter(ProtocolRow.protocol_id.in_(
        db.query(Protocol.id).filter(Protocol.document_id == document_id)
    )).delete(synchronize_session=False)
    db.query(Protocol).filter(Protocol.document_id == document_id).delete()
    protocol = Protocol(document_id=document_id)
    db.add(protocol)
    db.flush()
    persisted_rows: list[ProtocolRow] = []
    for idx, br in enumerate(built):
        prow = ProtocolRow(
            protocol_id=protocol.id, sort_order=idx,
            point_label=br.point_label, party_1_text=br.party_1_text,
            party_2_text=br.party_2_text, agreed_text=br.agreed_text,
            source_clause_key=br.source_clause_key, confidence=br.confidence,
            flags=br.flags, user_edited=False,
        )
        db.add(prow)
        persisted_rows.append(prow)
    # Flush so each ProtocolRow has its server-assigned UUID, then thread the
    # id back onto the BuiltRow so the ValidationEngine can emit row-level
    # TABLE_CELL_CHANGE warnings carrying `row_id`.
    db.flush()
    for br, prow in zip(built, persisted_rows):
        br.row_id = str(prow.id)
    # Rehydrate ResolverDiagnostic objects from preflight_diagnostics so the
    # ValidationEngine can fold them into REVISION/NUMBERING_MAPPING_MISMATCH
    # warnings on every (re)build. The `code` field is required by
    # ValidationEngine routing, so it must round-trip through metadata_json.
    from app.processing.types import ResolverDiagnostic
    diags_raw = ((doc.metadata_json or {}).get("preflight_diagnostics") or [])
    resolver_diags = [
        ResolverDiagnostic(
            level=d.get("level", "warning"),
            component=d.get("component", ""),
            code=d.get("code", "MAPPING_MISMATCH"),
            message=d.get("message", ""),
            block_id=d.get("block_id"),
        )
        for d in diags_raw
    ]
    # ValidationEngine receives ALL clauses (not just `changed`) so that
    # format-only revisions on otherwise-unchanged clauses are still tallied
    # in `format_only_revisions`.
    report = ValidationEngine().validate(built, clauses_dc, resolver_diags)
    doc.validation_report = {
        "textual_revisions_total": report.textual_revisions_total,
        "format_only_revisions": report.format_only_revisions,
        "covered_revisions": report.covered_revisions,
        "numbering_confidence_mean": report.numbering_confidence_mean,
        "warnings": report.warnings,
    }
    doc.status = DocumentStatus.BUILT
    db.commit()
    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol.id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    return ProtocolOut(id=protocol.id, document_id=document_id, rows=[_serialize_row(r) for r in rows])


@router.patch("/protocols/{protocol_id}/rows/{row_id}", response_model=ProtocolRowOut)
def patch_row(
    protocol_id: uuid.UUID,
    row_id: uuid.UUID,
    payload: ProtocolRowPatch,
    db: Session = Depends(get_db),
) -> ProtocolRowOut:
    row = db.get(ProtocolRow, row_id)
    if row is None or row.protocol_id != protocol_id:
        raise HTTPException(404, "Row not found")
    # Merge directive: append this row's text into the neighbour and delete self.
    if payload.merge_with in ("previous", "next"):
        siblings = (
            db.query(ProtocolRow)
            .filter(ProtocolRow.protocol_id == protocol_id)
            .order_by(ProtocolRow.sort_order)
            .all()
        )
        idx = next((i for i, r in enumerate(siblings) if r.id == row.id), -1)
        target = None
        if payload.merge_with == "previous" and idx > 0:
            target = siblings[idx - 1]
        elif payload.merge_with == "next" and 0 <= idx < len(siblings) - 1:
            target = siblings[idx + 1]
        if target is None:
            raise HTTPException(409, "No neighbouring row to merge with")
        for col in ("party_1_text", "party_2_text", "agreed_text"):
            existing = getattr(target, col) or ""
            extra = getattr(row, col) or ""
            joined = f"{existing}\n{extra}".strip("\n")
            setattr(target, col, joined)
        target.user_edited = True
        if "USER_EDITED" not in (target.flags or []):
            target.flags = [*list(target.flags or []), "USER_EDITED"]
        db.delete(row)
        db.commit()
        return _serialize_row(target)
    for col in ("point_label", "party_1_text", "party_2_text", "agreed_text"):
        val = getattr(payload, col)
        if val is not None:
            setattr(row, col, val)
    row.user_edited = True
    if "USER_EDITED" not in (row.flags or []):
        row.flags = [*list(row.flags or []), "USER_EDITED"]
    db.commit()
    return _serialize_row(row)


@router.post("/protocols/{protocol_id}/rows", response_model=ProtocolRowOut, status_code=201)
def add_row(
    protocol_id: uuid.UUID,
    payload: ProtocolRowCreate,
    db: Session = Depends(get_db),
) -> ProtocolRowOut:
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")
    existing = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    insert_at = payload.sort_order if payload.sort_order is not None else len(existing)
    insert_at = max(0, min(insert_at, len(existing)))
    # Shift rows at or after insert_at by +1.
    for r in existing:
        if r.sort_order >= insert_at:
            r.sort_order += 1
    new_row = ProtocolRow(
        protocol_id=protocol_id,
        sort_order=insert_at,
        point_label="",
        party_1_text="",
        party_2_text="",
        agreed_text="",
        source_clause_key=None,
        confidence=1.0,
        flags=["MANUALLY_ADDED"],
        user_edited=True,
    )
    db.add(new_row)
    db.commit()
    return _serialize_row(new_row)


@router.delete("/protocols/{protocol_id}/rows/{row_id}", status_code=204)
def delete_row(
    protocol_id: uuid.UUID,
    row_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    row = db.get(ProtocolRow, row_id)
    if row is None or row.protocol_id != protocol_id:
        raise HTTPException(404, "Row not found")
    deleted_order = row.sort_order
    db.delete(row)
    # Compact sort_order of subsequent rows.
    rest = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id, ProtocolRow.sort_order > deleted_order)
        .all()
    )
    for r in rest:
        r.sort_order -= 1
    db.commit()
    return None


@router.get("/protocols/{protocol_id}/rows", response_model=ProtocolOut)
def get_protocol_rows(
    protocol_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ProtocolOut:
    """Return the existing protocol rows without rebuilding.

    The frontend calls this when navigating back to a protocol that was already
    built — calling POST /documents/{id}/protocol again would wipe and rebuild,
    losing manual edits.
    """
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")
    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    return ProtocolOut(
        id=protocol.id,
        document_id=protocol.document_id,
        rows=[_serialize_row(r) for r in rows],
    )


@router.get("/protocols", response_model=list[ProtocolOut])
def list_protocols_for_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[ProtocolOut]:
    """List protocols for a document. Used by the frontend to decide whether
    to rebuild (no protocol yet) or load existing rows."""
    protocols = db.query(Protocol).filter(Protocol.document_id == document_id).all()
    out: list[ProtocolOut] = []
    for protocol in protocols:
        rows = (
            db.query(ProtocolRow)
            .filter(ProtocolRow.protocol_id == protocol.id)
            .order_by(ProtocolRow.sort_order)
            .all()
        )
        out.append(ProtocolOut(
            id=protocol.id,
            document_id=protocol.document_id,
            rows=[_serialize_row(r) for r in rows],
        ))
    return out


@router.post("/protocols/{protocol_id}/swap-parties", response_model=ProtocolOut)
def swap_parties(
    protocol_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ProtocolOut:
    """Flip the drafting party for the protocol's document.

    The data model invariant is that column 2 (`party_1_text`) holds the
    original-document text and column 3 (`party_2_text`) holds the accepted
    (drafting-side) text — these column values are NOT swapped. What changes
    is `Document.drafting_party_id`: the column header labels (e.g.
    "Редакция Арендодателя" / "Редакция Арендатора") and the default
    `agreed_text` are derived from the current drafting party at response
    time. Rows the user has not edited (`row.user_edited == False`) get
    `agreed_text` recomputed against the new drafting party. Rows with
    `user_edited == True` are left intact regardless of the current
    `agreed_text` value — the user may have manually changed `point_label`
    or `party_1_text` while leaving `agreed_text` at its auto-generated
    string, and we must respect their edit by not touching the row.
    """
    protocol = db.get(Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(404, "Protocol not found")
    doc = db.get(Document, protocol.document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    parties = db.query(Party).filter(Party.document_id == doc.id).all()
    if len(parties) != 2:
        raise HTTPException(409, "Swap requires exactly two parties")
    old_drafting = next((p for p in parties if p.id == doc.drafting_party_id), None)
    other = next((p for p in parties if p.id != doc.drafting_party_id), None)
    if old_drafting is None or other is None:
        raise HTTPException(409, "Drafting party not set")
    # Compute the auto-generated agreed_text for the new drafting party.
    new_agreed = agreed_text_for_party(other.role)
    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol_id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    for r in rows:
        # Recalculate only rows the user has not edited. We use the explicit
        # user_edited flag rather than comparing agreed_text against the old
        # auto-label, because the user may have edited point_label or
        # party_1_text while leaving agreed_text alone — that row is still
        # "user-edited" and must not be silently rewritten.
        if not r.user_edited:
            r.agreed_text = new_agreed
    doc.drafting_party_id = other.id
    db.commit()
    return ProtocolOut(
        id=protocol.id,
        document_id=protocol.document_id,
        rows=[_serialize_row(r) for r in rows],
    )
```

> **Merge semantics:** the frontend invokes a row merge by PATCHing the row
> being absorbed with `{"merge_with": "previous"}` or `{"merge_with": "next"}`.
> The server appends that row's text columns into the neighbour, marks the
> neighbour as `user_edited`, and deletes the absorbed row in the same
> transaction. The response is the merged neighbour row.

- [ ] **Step 2: Write the failing test `backend/tests/api/test_protocols.py`**

```python
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.clause import Clause as ClauseModel


@pytest.fixture
def doc_with_changes():
    db = SessionLocal()
    doc = Document(id=uuid.uuid4(), original_filename="t.docx", storage_key="k",
                   contract_name="Договор", status=DocumentStatus.PARTIES_CONFIRMED,
                   preflight_metrics={"revisions_total": 1, "format_only_count": 0, "paragraphs_with_numbering": 1, "numbering_confidence_mean": 1.0})
    db.add(doc)
    p1 = Party(document_id=doc.id, name="ООО Ромашка", role="Арендодатель", confidence=0.9)
    p2 = Party(document_id=doc.id, name="АО Василёк", role="Арендатор", confidence=0.9)
    db.add_all([p1, p2])
    db.flush()
    doc.drafting_party_id = p2.id
    db.add(ClauseModel(
        document_id=doc.id, clause_key="c_p_0001", label="1.", level=0, parent_key=None,
        sort_order=0, original_text="Старый", accepted_text="Новый",
        flags=[], confidence=1.0, revisions=[{"type": "INS", "text": "Новый", "author": ""}],
    ))
    db.commit()
    yield doc, p1, p2
    db.query(ClauseModel).filter(ClauseModel.document_id == doc.id).delete()
    db.delete(p1); db.delete(p2); db.delete(doc); db.commit(); db.close()


def test_build_protocol_creates_rows(doc_with_changes):
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        assert r.status_code == 201, r.text
        body = r.json()
        assert len(body["rows"]) == 1
        row = body["rows"][0]
        assert row["point_label"] == "1."
        assert row["party_1_text"] == "Старый"
        assert row["party_2_text"] == "Новый"
        assert row["agreed_text"] == "Редакция Арендатора"


def test_patch_row_marks_user_edited(doc_with_changes):
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        r2 = client.patch(f"/api/protocols/{proto['id']}/rows/{row_id}", json={"agreed_text": "Согласовано"})
        assert r2.status_code == 200
        assert r2.json()["user_edited"] is True
        assert r2.json()["agreed_text"] == "Согласовано"


def test_swap_parties_keeps_columns_and_updates_agreed_text(doc_with_changes):
    """Swapping flips the drafting party and recomputes auto-generated
    agreed_text on rows the user has not edited. Column values for
    party_1_text/party_2_text MUST NOT change — they are bound to the
    original-vs-accepted data, not to which party is currently drafting."""
    doc, p1, p2 = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        before = proto["rows"][0]
        assert before["party_1_text"] == "Старый"
        assert before["party_2_text"] == "Новый"
        # drafting starts as p2 (Арендатор) → agreed_text is "Редакция Арендатора".
        assert before["agreed_text"] == "Редакция Арендатора"
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        after = r2.json()["rows"][0]
        # Columns 2 and 3 unchanged — invariant holds.
        assert after["party_1_text"] == "Старый"
        assert after["party_2_text"] == "Новый"
        # Auto-generated agreed_text was rewritten to the new drafting role.
        assert after["agreed_text"] == "Редакция Арендодателя"


def test_swap_parties_preserves_user_edited_agreed_text(doc_with_changes):
    """Rows whose agreed_text was manually edited keep their custom value
    after a swap (we recompute only rows where user_edited == False)."""
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        client.patch(f"/api/protocols/{proto['id']}/rows/{row_id}",
                     json={"agreed_text": "Согласовано вручную"})
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        assert r2.json()["rows"][0]["agreed_text"] == "Согласовано вручную"


def test_swap_parties_skips_user_edited_row_even_when_agreed_text_is_auto(doc_with_changes):
    """A row marked user_edited=True (e.g. user changed point_label or
    party_1_text but left agreed_text at the auto-generated value) keeps
    its agreed_text after a swap — we trust the explicit user_edited flag,
    not a string comparison against the old auto-label."""
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        # User edits point_label only; agreed_text stays at "Редакция Арендатора".
        client.patch(f"/api/protocols/{proto['id']}/rows/{row_id}",
                     json={"point_label": "1.1."})
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        after = r2.json()["rows"][0]
        # user_edited=True wins: agreed_text is NOT recomputed.
        assert after["user_edited"] is True
        assert after["agreed_text"] == "Редакция Арендатора"


def test_swap_parties_recomputes_when_user_edited_false(doc_with_changes):
    """Sanity check the inverse: a row with user_edited=False has its
    agreed_text recomputed to the new drafting role's auto-label."""
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        # No edits — user_edited stays False on the freshly-built row.
        assert proto["rows"][0]["user_edited"] is False
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        assert r2.json()["rows"][0]["agreed_text"] == "Редакция Арендодателя"


def test_get_protocol_rows_returns_existing_without_rebuild(doc_with_changes):
    """GET /protocols/{pid}/rows returns the persisted rows (including user
    edits) without triggering a rebuild that would wipe them."""
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        client.patch(f"/api/protocols/{proto['id']}/rows/{row_id}",
                     json={"agreed_text": "Согласовано"})
        r2 = client.get(f"/api/protocols/{proto['id']}/rows")
        assert r2.status_code == 200
        body = r2.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["agreed_text"] == "Согласовано"
        assert body["rows"][0]["user_edited"] is True


def test_list_protocols_for_document(doc_with_changes):
    """GET /protocols?document_id=... returns the protocol(s) for a document
    so the frontend can decide whether to load or build."""
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        # Before build — empty list.
        r0 = client.get(f"/api/protocols", params={"document_id": str(doc.id)})
        assert r0.status_code == 200
        assert r0.json() == []
        # After build — one protocol.
        client.post(f"/api/documents/{doc.id}/protocol")
        r1 = client.get(f"/api/protocols", params={"document_id": str(doc.id)})
        assert r1.status_code == 200
        body = r1.json()
        assert len(body) == 1
        assert body[0]["document_id"] == str(doc.id)


def test_add_row_appends_empty_user_added_row(doc_with_changes):
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        r2 = client.post(f"/api/protocols/{proto['id']}/rows", json={})
        assert r2.status_code == 201, r2.text
        body = r2.json()
        assert body["point_label"] == ""
        assert "MANUALLY_ADDED" in body["flags"]
        assert body["user_edited"] is True


def test_delete_row_removes_row(doc_with_changes):
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        r2 = client.delete(f"/api/protocols/{proto['id']}/rows/{row_id}")
        assert r2.status_code == 204
```

- [ ] **Step 3: Run the test, expect pass**

Run: `cd backend && pytest tests/api/test_protocols.py -v`
Expected: 10 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/protocols.py backend/tests/api/test_protocols.py
git commit -m "feat(api): add protocol build and row patch endpoints"
```

---

## Task 13: DOCX export + download endpoint

**Files:**
- Create: `backend/app/services/exporter.py`
- Modify: `backend/app/api/protocols.py` (add export endpoint)
- Modify: `backend/app/api/files.py` (raw input download)
- Test: `backend/tests/services/test_exporter.py`
- Test: `backend/tests/api/test_export.py`

- [ ] **Step 1: Create `backend/app/services/exporter.py`**

```python
from __future__ import annotations
from io import BytesIO
from docx import Document as DocxDocument
from docx.shared import Pt


class ProtocolExporter:
    def export(
        self,
        rows: list[dict],
        drafting_role: str,
        counterparty_role: str,
        contract_name: str | None,
    ) -> bytes:
        doc = DocxDocument()
        title = f"Протокол разногласий к договору {contract_name}" if contract_name else "Протокол разногласий"
        h = doc.add_heading(title, level=1)
        for run in h.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(14)
        table = doc.add_table(rows=1 + len(rows), cols=4)
        table.style = "Table Grid"
        headers = [
            "Пункт договора",
            f"Редакция {counterparty_role}" if counterparty_role else "Редакция Стороны 1",
            f"Редакция {drafting_role}" if drafting_role else "Редакция Стороны 2",
            "Согласованная редакция",
        ]
        for i, h_text in enumerate(headers):
            cell = table.rows[0].cells[i]
            cell.text = h_text
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(11)
        for r_idx, row in enumerate(rows, start=1):
            cells = table.rows[r_idx].cells
            cells[0].text = row["point_label"]
            cells[1].text = row["party_1_text"]
            cells[2].text = row["party_2_text"]
            cells[3].text = row["agreed_text"]
            for cell in cells:
                for p in cell.paragraphs:
                    for run in p.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(11)
        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
```

- [ ] **Step 2: Append export endpoint to `backend/app/api/protocols.py`**

Append after the `patch_row` function:

```python
import io
import re
import urllib.parse
from fastapi import Response

from app.schemas.protocol import ExportRequest
from app.services.exporter import ProtocolExporter

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya", " ": "_",
}


def _sanitize_filename(name: str) -> str:
    n = name.strip().replace("/", "").replace("\\", "")
    n = re.sub(r"[\x00-\x1f\x7f]", "", n)
    if len(n) > 200:
        n = n[:200]
    return n or "Протокол_разногласий"


def _ascii_fallback(name: str) -> str:
    out = []
    for ch in name:
        low = ch.lower()
        if low in _TRANSLIT:
            translit = _TRANSLIT[low]
            out.append(translit if ch == low else translit.capitalize())
        elif ch.isascii() and (ch.isalnum() or ch in "._-"):
            out.append(ch)
        else:
            out.append("_")
    res = "".join(out).strip("_")
    return res or "protocol"


@router.post("/documents/{document_id}/protocol/export")
def export_protocol(document_id: uuid.UUID, payload: ExportRequest, db: Session = Depends(get_db)) -> Response:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    parties = db.query(Party).filter(Party.document_id == document_id).all()
    drafting = next((p for p in parties if p.id == doc.drafting_party_id), None)
    counterparty = next((p for p in parties if p.id != doc.drafting_party_id), None) if drafting else None
    if drafting is None or counterparty is None:
        raise HTTPException(409, "Parties not finalized")
    protocol = db.query(Protocol).filter(Protocol.document_id == document_id).one_or_none()
    if protocol is None:
        raise HTTPException(409, "Protocol not built")
    rows = (
        db.query(ProtocolRow)
        .filter(ProtocolRow.protocol_id == protocol.id)
        .order_by(ProtocolRow.sort_order)
        .all()
    )
    payload_rows = [
        {
            "point_label": r.point_label,
            "party_1_text": r.party_1_text,
            "party_2_text": r.party_2_text,
            "agreed_text": r.agreed_text,
        }
        for r in rows
    ]
    data = ProtocolExporter().export(payload_rows, drafting.role, counterparty.role, doc.contract_name)
    name = _sanitize_filename(payload.filename)
    ascii_name = _ascii_fallback(name) + ".docx"
    utf8_name = urllib.parse.quote(name + ".docx", safe="")
    headers = {
        "Content-Disposition": f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{utf8_name}',
    }
    doc.status = DocumentStatus.EXPORTED
    db.commit()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )
```

- [ ] **Step 3: Update `backend/app/api/files.py`** (raw input download for preview support)

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.services.storage import S3Storage

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{document_id}/input.docx")
def download_input(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    data = S3Storage().get(doc.storage_key)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
```

- [ ] **Step 4: Write the failing test `backend/tests/services/test_exporter.py`**

```python
from io import BytesIO
from docx import Document
from app.services.exporter import ProtocolExporter


def test_export_produces_docx_with_4col_table_and_headers():
    rows = [{"point_label": "1.", "party_1_text": "old", "party_2_text": "new", "agreed_text": "Редакция Арендатора"}]
    data = ProtocolExporter().export(rows, drafting_role="Арендатор", counterparty_role="Арендодатель", contract_name="Договор")
    doc = Document(BytesIO(data))
    assert any("Протокол разногласий" in p.text for p in doc.paragraphs)
    assert len(doc.tables) == 1
    table = doc.tables[0]
    assert len(table.columns) == 4
    headers = [c.text for c in table.rows[0].cells]
    assert headers == ["Пункт договора", "Редакция Арендодатель", "Редакция Арендатор", "Согласованная редакция"]
    body = [c.text for c in table.rows[1].cells]
    assert body == ["1.", "old", "new", "Редакция Арендатора"]


def test_export_falls_back_to_storona_labels_for_empty_roles():
    rows = [{"point_label": "1.", "party_1_text": "a", "party_2_text": "b", "agreed_text": "c"}]
    data = ProtocolExporter().export(rows, drafting_role="", counterparty_role="", contract_name=None)
    doc = Document(BytesIO(data))
    headers = [c.text for c in doc.tables[0].rows[0].cells]
    assert headers[1] == "Редакция Стороны 1"
    assert headers[2] == "Редакция Стороны 2"
```

- [ ] **Step 5: Run exporter test, expect pass**

Run: `cd backend && pytest tests/services/test_exporter.py -v`
Expected: 2 passed.

- [ ] **Step 6: Write the failing test `backend/tests/api/test_export.py`**

```python
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.clause import Clause as ClauseModel


@pytest.fixture
def ready_doc():
    db = SessionLocal()
    doc = Document(id=uuid.uuid4(), original_filename="t.docx", storage_key="k",
                   contract_name="Договор", status=DocumentStatus.PARTIES_CONFIRMED,
                   preflight_metrics={"revisions_total": 1, "format_only_count": 0,
                                      "paragraphs_with_numbering": 1, "numbering_confidence_mean": 1.0})
    db.add(doc)
    p1 = Party(document_id=doc.id, name="ООО Ромашка", role="Арендодатель", confidence=0.9)
    p2 = Party(document_id=doc.id, name="АО Василёк", role="Арендатор", confidence=0.9)
    db.add_all([p1, p2]); db.flush()
    doc.drafting_party_id = p2.id
    db.add(ClauseModel(
        document_id=doc.id, clause_key="c_p_0001", label="1.", level=0, parent_key=None,
        sort_order=0, original_text="Старый", accepted_text="Новый",
        flags=[], confidence=1.0, revisions=[{"type": "INS", "text": "Новый", "author": ""}],
    ))
    db.commit()
    yield doc
    db.query(ClauseModel).filter(ClauseModel.document_id == doc.id).delete()
    db.query(Party).filter(Party.document_id == doc.id).delete()
    db.delete(doc); db.commit(); db.close()


def test_export_endpoint_returns_docx_bytes(ready_doc):
    with TestClient(app) as client:
        client.post(f"/api/documents/{ready_doc.id}/protocol")
        r = client.post(f"/api/documents/{ready_doc.id}/protocol/export", json={"filename": "Протокол"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        cd = r.headers["content-disposition"]
        assert "filename=" in cd
        assert "filename*=UTF-8''" in cd
        assert r.content[:2] == b"PK"
```

- [ ] **Step 7: Run export endpoint test, expect pass**

Run: `cd backend && pytest tests/api/test_export.py -v`
Expected: 1 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/exporter.py backend/app/api/protocols.py backend/app/api/files.py backend/tests/services/test_exporter.py backend/tests/api/test_export.py
git commit -m "feat(api): add DOCX export endpoint and raw input download"
```

---

## Task 14: Frontend bootstrap + API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/types.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "disprot-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.13",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@tanstack/react-table": "8.20.5",
    "@tanstack/react-query": "5.59.0",
    "tailwindcss": "3.4.13",
    "autoprefixer": "10.4.20",
    "postcss": "8.4.47"
  },
  "devDependencies": {
    "typescript": "5.6.2",
    "@types/react": "18.3.10",
    "@types/react-dom": "18.3.0",
    "@types/node": "22.7.4",
    "vitest": "2.1.1",
    "@vitejs/plugin-react": "4.3.1",
    "@testing-library/react": "16.0.1",
    "@testing-library/user-event": "14.5.2",
    "@testing-library/jest-dom": "6.5.0",
    "jsdom": "25.0.0",
    "msw": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] },
    "types": ["node", "vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules", "vitest.config.ts"]
}
```

Note: `"node"` is required because `vitest.config.ts` uses Node built-ins
(`path`) and `__dirname`. `vitest.config.ts` is added to `"exclude"` so
that the Next.js typecheck (which uses this same `tsconfig.json`) does
not pull the vitest config into its program — vitest itself loads the
config through its own toolchain and does not need it included here.

- [ ] **Step 3: Create `frontend/next.config.mjs`**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
  },
};
export default nextConfig;
```

- [ ] **Step 4: Create `frontend/tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
export default config;
```

- [ ] **Step 5: Create `frontend/postcss.config.mjs`**

```js
export default { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 6: Create `frontend/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body { font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
```

- [ ] **Step 7: Create `frontend/app/layout.tsx`**

```tsx
import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "Протокол разногласий" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
```

- [ ] **Step 8: Create `frontend/lib/types.ts`**

```ts
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
```

- [ ] **Step 9: Create `frontend/lib/api.ts`**

```ts
import type { AnalysisOut, Protocol, ProtocolRow, UUID } from "./types";

const BASE = "";

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
  return resp.json() as Promise<T>;
}

export const api = {
  uploadDocument: async (file: File): Promise<{ id: UUID; status: string }> => {
    const fd = new FormData();
    fd.append("file", file);
    return jsonOrThrow(await fetch(`${BASE}/api/documents`, { method: "POST", body: fd }));
  },
  getAnalysis: async (id: UUID): Promise<AnalysisOut> =>
    jsonOrThrow(await fetch(`${BASE}/api/documents/${id}/analysis`)),
  // PartiesPatchItem mirrors the backend `PartyUpdateItem` schema (Task 11):
  //   id: existing party UUID, or null to create a new party.
  // Omitting an existing party id from the list deletes that party.
  patchParties: async (
    id: UUID,
    parties: { id: UUID | null; name: string; role: string }[],
    drafting: UUID | null,
  ): Promise<AnalysisOut> =>
    jsonOrThrow(await fetch(`${BASE}/api/documents/${id}/parties`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parties, drafting_party_id: drafting }),
    })),
  buildProtocol: async (id: UUID): Promise<Protocol> =>
    jsonOrThrow(await fetch(`${BASE}/api/documents/${id}/protocol`, { method: "POST" })),
  listProtocolsForDocument: async (documentId: UUID): Promise<Protocol[]> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols?document_id=${documentId}`)),
  getProtocolRows: async (protocolId: UUID): Promise<Protocol> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/rows`)),
  patchRow: async (
    protocolId: UUID,
    rowId: UUID,
    patch: Partial<ProtocolRow> & { merge_with?: "previous" | "next" },
  ): Promise<ProtocolRow> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/rows/${rowId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    })),
  addRow: async (protocolId: UUID, sortOrder?: number): Promise<ProtocolRow> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/rows`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sort_order: sortOrder ?? null }),
    })),
  deleteRow: async (protocolId: UUID, rowId: UUID): Promise<void> => {
    const r = await fetch(`${BASE}/api/protocols/${protocolId}/rows/${rowId}`, { method: "DELETE" });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  },
  swapParties: async (protocolId: UUID): Promise<Protocol> =>
    jsonOrThrow(await fetch(`${BASE}/api/protocols/${protocolId}/swap-parties`, { method: "POST" })),
  exportProtocol: async (documentId: UUID, filename: string): Promise<Blob> => {
    const r = await fetch(`${BASE}/api/documents/${documentId}/protocol/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename }),
    });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.blob();
  },
};
```

- [ ] **Step 10: Install + smoke build**

Run: `cd frontend && npm install && npx next build`
Expected: build succeeds (creates `.next/`).

- [ ] **Step 11: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './vitest.setup.ts',
  },
})
```

- [ ] **Step 12: Create `frontend/src/mocks/server.ts`**

```ts
import { setupServer } from 'msw/node'

export const server = setupServer()
```

- [ ] **Step 12b: Create `frontend/vitest.setup.ts`**

```ts
import '@testing-library/jest-dom'
import { server } from './src/mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

- [ ] **Step 13: Verify vitest starts**

Run: `cd frontend && npm test -- --passWithNoTests --reporter=verbose`
Expected: exits 0 with "No test files found".

- [ ] **Step 14: Commit**

```bash
git add frontend
git commit -m "feat(frontend): bootstrap Next.js app with API client, types, and vitest"
```

---

## Task 15: Upload screen

**Files:**
- Create: `frontend/components/FileUpload.tsx`
- Create: `frontend/app/page.tsx`

- [ ] **Step 1: Create `frontend/components/FileUpload.tsx`**

```tsx
"use client";
import { useState, type DragEvent, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function FileUpload() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handle = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.uploadDocument(file);
      router.push(`/documents/${res.id}/analysis`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) handle(f);
  };
  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handle(f);
  };

  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center bg-white"
    >
      <p className="mb-4 text-lg">Перетащите .docx сюда или выберите файл</p>
      <label className="inline-block px-4 py-2 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700">
        Выбрать файл
        <input type="file" accept=".docx" onChange={onPick} className="hidden" />
      </label>
      {busy && <p className="mt-4 text-gray-500">Загружаем...</p>}
      {error && <p className="mt-4 text-red-600">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/app/page.tsx`**

```tsx
import { FileUpload } from "@/components/FileUpload";

export default function Home() {
  return (
    <main className="max-w-3xl mx-auto py-16 px-4">
      <h1 className="text-3xl font-semibold mb-8">Протокол разногласий</h1>
      <FileUpload />
    </main>
  );
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx next build`
Expected: build succeeds, no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components frontend/app/page.tsx
git commit -m "feat(frontend): add upload screen with drag-and-drop"
```

---

## Task 16: Preflight + Parties screens

**Files:**
- Create: `frontend/components/PartySelector.tsx`
- Create: `frontend/app/documents/[id]/analysis/page.tsx`
- Create: `frontend/app/documents/[id]/parties/page.tsx`

- [ ] **Step 1: Create `frontend/app/documents/[id]/analysis/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut } from "@/lib/types";

export default function AnalysisPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const a = await api.getAnalysis(params.id);
        if (cancelled) return;
        setAnalysis(a);
        if (a.status === "parsed" || a.status === "parties_confirmed") return;
        if (a.status === "failed") {
          setError("Ошибка обработки документа");
          return;
        }
        setTimeout(tick, 1000);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    tick();
    return () => { cancelled = true; };
  }, [params.id]);

  if (error) return <main className="p-8 text-red-600">{error}</main>;
  if (!analysis) return <main className="p-8">Анализируем документ…</main>;
  if (analysis.status !== "parsed" && analysis.status !== "parties_confirmed") {
    return <main className="p-8">Анализируем документ…</main>;
  }

  const m = analysis.preflight_metrics;
  const diagnostics = analysis.preflight_diagnostics ?? [];
  return (
    <main className="max-w-3xl mx-auto py-12 px-4 space-y-6">
      <h1 className="text-2xl font-semibold">Предварительный отчёт</h1>
      {m && (
        <div className="bg-white border rounded p-4 space-y-1">
          <div>Правок всего: {m.revisions_total}</div>
          <div>Format-only: {m.format_only_count}</div>
          <div>Параграфов с нумерацией: {m.paragraphs_with_numbering}</div>
          <div>Уверенность нумерации: {(m.numbering_confidence_mean * 100).toFixed(0)}%</div>
        </div>
      )}
      {diagnostics.length > 0 && (
        <div className="bg-white border rounded p-4 space-y-2">
          <div className="font-medium">Диагностика</div>
          <ul className="space-y-1 text-sm">
            {diagnostics.map((d, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  aria-hidden
                  className={
                    d.level === "error"
                      ? "inline-block mt-0.5 text-red-600"
                      : "inline-block mt-0.5 text-yellow-600"
                  }
                  title={d.level}
                >
                  {d.level === "error" ? "⛔" : "⚠"}
                </span>
                <span>
                  <span className="font-mono text-gray-700">{d.component}</span>
                  {": "}
                  <span>{d.message}</span>
                  {d.block_id && (
                    <span className="text-gray-500"> ({d.block_id})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <button
        onClick={() => router.push(`/documents/${params.id}/parties`)}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Дальше
      </button>
    </main>
  );
}
```

- [ ] **Step 2: Create `frontend/components/PartySelector.tsx`**

The PartySelector must let the user add and remove party rows in addition to
editing existing ones. The PartyExtractor (Task 6) may return zero or one
party for documents where the regexes do not match — without add/remove
controls the user gets stuck. New parties are tracked with `id: null` and
a stable client-side `_uid` (so React keys remain stable while id is null);
the backend `PATCH /api/documents/{id}/parties` accepts items with
`id: null` (creates a new party) and treats omitted existing party ids as
deletions (see Task 11 `update_parties` handler).

```tsx
"use client";

export interface PartyDraft {
  id: string | null;
  name: string;
  role: string;
  _uid: string;
}

interface Props {
  parties: PartyDraft[];
  draftingUid: string | null;
  onChange: (parties: PartyDraft[]) => void;
  onDraftingChange: (uid: string | null) => void;
}

let UID_SEQ = 0;
export const newPartyUid = () => `p${++UID_SEQ}_${Date.now()}`;

export function PartySelector({ parties, draftingUid, onChange, onDraftingChange }: Props) {
  const update = (idx: number, patch: Partial<PartyDraft>) => {
    const next = parties.map((p, i) => (i === idx ? { ...p, ...patch } : p));
    onChange(next);
  };
  const add = () => {
    const draft: PartyDraft = { id: null, name: "", role: "", _uid: newPartyUid() };
    onChange([...parties, draft]);
  };
  const remove = (idx: number) => {
    const removed = parties[idx];
    const next = parties.filter((_, i) => i !== idx);
    onChange(next);
    if (removed && removed._uid === draftingUid) onDraftingChange(null);
  };
  return (
    <div className="space-y-3">
      {parties.map((p, idx) => (
        <div key={p._uid} className="flex items-start gap-3 bg-white border rounded p-3">
          <input
            type="radio"
            name="drafting"
            checked={draftingUid === p._uid}
            onChange={() => onDraftingChange(p._uid)}
            className="mt-2"
          />
          <div className="grid grid-cols-2 gap-2 flex-1">
            <input
              className="border rounded px-2 py-1"
              value={p.name}
              onChange={(e) => update(idx, { name: e.target.value })}
              placeholder="Наименование"
            />
            <input
              className="border rounded px-2 py-1"
              value={p.role}
              onChange={(e) => update(idx, { role: e.target.value })}
              placeholder="Роль"
            />
          </div>
          <button
            type="button"
            onClick={() => remove(idx)}
            className="text-red-600 text-sm hover:underline"
          >
            Удалить
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="px-3 py-1 border border-dashed border-gray-400 rounded text-sm text-gray-700 hover:bg-gray-50"
      >
        + Добавить сторону
      </button>
    </div>
  );
}
```

- [ ] **Step 2a: Add a unit test `frontend/__tests__/PartySelector.test.tsx`**

Verifies that the PATCH payload shape matches the backend contract:
existing parties keep their `id`, newly-added parties carry `id: null`,
and removing an existing party simply omits it from the list. The test
uses `@testing-library/react`.

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { useState } from "react";
import { PartySelector, type PartyDraft, newPartyUid } from "@/components/PartySelector";

function Harness({ initial, onSubmit }: { initial: PartyDraft[]; onSubmit: (p: PartyDraft[]) => void }) {
  const [parties, setParties] = useState<PartyDraft[]>(initial);
  const [drafting, setDrafting] = useState<string | null>(null);
  return (
    <>
      <PartySelector parties={parties} draftingUid={drafting} onChange={setParties} onDraftingChange={setDrafting} />
      <button onClick={() => onSubmit(parties)}>submit</button>
    </>
  );
}

test("add new party then remove existing produces correct PATCH shape", () => {
  const existing: PartyDraft = { id: "uuid-existing", name: "ООО А", role: "Арендодатель", _uid: newPartyUid() };
  const captured: PartyDraft[][] = [];
  render(<Harness initial={[existing]} onSubmit={(p) => captured.push(p)} />);
  fireEvent.click(screen.getByText("+ Добавить сторону"));
  // Two name inputs now visible (existing + new).
  const nameInputs = screen.getAllByPlaceholderText("Наименование");
  fireEvent.change(nameInputs[1], { target: { value: "АО Б" } });
  const roleInputs = screen.getAllByPlaceholderText("Роль");
  fireEvent.change(roleInputs[1], { target: { value: "Арендатор" } });
  // Remove the original existing party.
  fireEvent.click(screen.getAllByText("Удалить")[0]);
  fireEvent.click(screen.getByText("submit"));
  const final = captured.at(-1)!;
  expect(final).toHaveLength(1);
  expect(final[0].id).toBeNull();
  expect(final[0].name).toBe("АО Б");
  expect(final[0].role).toBe("Арендатор");
  // Mapping to PATCH payload (mirrors PartiesPage.submit):
  const payload = final.map((p) => ({ id: p.id, name: p.name, role: p.role }));
  expect(payload).toEqual([{ id: null, name: "АО Б", role: "Арендатор" }]);
});
```

Run: `cd frontend && npm test -- PartySelector.test.tsx`
Expected: 1 passed.

- [ ] **Step 3: Create `frontend/app/documents/[id]/parties/page.tsx`**

If the user navigates back to this screen after a protocol has already been
built and edited, we must NOT call `api.buildProtocol()` again — the build
endpoint is wipe-and-rebuild and would discard the user's row edits. We
check for an existing protocol first and skip straight to the table.

> Note: if the user truly wants a fresh rebuild after row edits (e.g. they
> changed party names and want auto-generated `agreed_text` regenerated for
> all rows), they must delete the existing protocol first. The MVP UI does
> not expose a delete-protocol button — it can be done via API. This is a
> deliberate trade-off: edit preservation matters more than rebuild
> ergonomics for the MVP.

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut } from "@/lib/types";
import { PartySelector, newPartyUid, type PartyDraft } from "@/components/PartySelector";

export default function PartiesPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [parties, setParties] = useState<PartyDraft[]>([]);
  // We track the drafting selection by the client-side _uid because newly-
  // added parties have no server id yet; on submit we resolve _uid → real
  // UUID after the PATCH response returns.
  const [draftingUid, setDraftingUid] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    api.getAnalysis(params.id).then((a) => {
      setAnalysis(a);
      const drafts: PartyDraft[] = a.parties.map((p) => ({
        id: p.id, name: p.name, role: p.role, _uid: newPartyUid(),
      }));
      setParties(drafts);
      const draftingDraft = drafts.find((d) => d.id === a.drafting_party_id) ?? null;
      setDraftingUid(draftingDraft?._uid ?? null);
    }).catch((e) => setError((e as Error).message));
  }, [params.id]);

  const submit = async () => {
    if (!draftingUid) return;
    setBusy(true);
    try {
      const payload = parties.map((p) => ({ id: p.id, name: p.name, role: p.role }));
      // First-pass PATCH: drafting may be a brand-new (id=null) party,
      // in which case we cannot send drafting_party_id yet — resolve it
      // from the response and PATCH a second time if needed.
      const draftingDraft = parties.find((p) => p._uid === draftingUid)!;
      const firstResp = await api.patchParties(
        params.id, payload,
        draftingDraft.id ?? null,
      );
      if (!draftingDraft.id) {
        // Locate the newly-created party by (name, role) and confirm drafting.
        const created = firstResp.parties.find(
          (p) => p.name === draftingDraft.name && p.role === draftingDraft.role,
        );
        if (created) {
          await api.patchParties(params.id, firstResp.parties.map((p) => ({
            id: p.id, name: p.name, role: p.role,
          })), created.id);
        }
      }
      // Preserve existing edits on back-navigation: only build if no
      // protocol exists yet for this document.
      const existing = await api.listProtocolsForDocument(params.id);
      if (existing.length > 0) {
        router.push(`/documents/${params.id}/protocol`);
        return;
      }
      await api.buildProtocol(params.id);
      router.push(`/documents/${params.id}/protocol`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (error) return <main className="p-8 text-red-600">{error}</main>;
  if (!analysis) return <main className="p-8">Загружаем…</main>;

  return (
    <main className="max-w-3xl mx-auto py-12 px-4 space-y-6">
      <h1 className="text-2xl font-semibold">Стороны договора</h1>
      <PartySelector
        parties={parties}
        draftingUid={draftingUid}
        onChange={setParties}
        onDraftingChange={setDraftingUid}
      />
      <p className="text-sm text-gray-600">
        Отметьте сторону, от чьего имени составляется протокол (drafting party).
      </p>
      <button
        disabled={!draftingUid || busy || parties.length !== 2}
        onClick={submit}
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-gray-300"
      >
        Построить протокол
      </button>
      {parties.length !== 2 && (
        <p className="text-amber-700 text-sm">MVP поддерживает ровно две стороны.</p>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npx next build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/PartySelector.tsx frontend/app/documents
git commit -m "feat(frontend): add preflight and parties screens"
```

---

## Task 17: Protocol table screen

**Files:**
- Create: `frontend/components/ProtocolTable.tsx`
- Create: `frontend/app/documents/[id]/protocol/page.tsx`

- [ ] **Step 1: Create `frontend/components/ProtocolTable.tsx`**

```tsx
'use client'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useState, useCallback } from 'react'
import type { ProtocolRow } from '@/lib/types'

interface ProtocolTableProps {
  rows: ProtocolRow[]
  draftingRole: string
  counterpartyRole: string
  onPatch: (rowId: string, patch: Partial<ProtocolRow>) => Promise<void>
  onDelete: (rowId: string) => Promise<void>
  onMerge: (rowId: string, direction: 'previous' | 'next') => Promise<void>
  onAddRow: () => Promise<void>
  onSwapParties: () => Promise<void>
}

const columnHelper = createColumnHelper<ProtocolRow>()

export default function ProtocolTable({
  rows,
  draftingRole,
  counterpartyRole,
  onPatch,
  onDelete,
  onMerge,
  onAddRow,
  onSwapParties,
}: ProtocolTableProps) {
  const [editingCell, setEditingCell] = useState<{rowId: string; field: string} | null>(null)

  const handleCellBlur = useCallback(
    async (rowId: string, field: keyof ProtocolRow, originalValue: string, newValue: string) => {
      setEditingCell(null)
      if (newValue === originalValue) return  // no-op: value unchanged, don't mark user_edited
      await onPatch(rowId, { [field]: newValue } as Partial<ProtocolRow>)
    },
    [onPatch],
  )

  const columns = [
    columnHelper.accessor('point_label', {
      header: 'Пункт договора',
      cell: ({ row, getValue }) =>
        editingCell?.rowId === row.original.id && editingCell.field === 'point_label' ? (
          <input
            autoFocus
            defaultValue={getValue()}
            onBlur={(e) => handleCellBlur(row.original.id, 'point_label', getValue(), e.target.value)}
            className="w-full border-none outline-none bg-transparent"
          />
        ) : (
          <span
            role="cell"
            onClick={() => setEditingCell({ rowId: row.original.id, field: 'point_label' })}
            className="cursor-pointer block min-h-[1.5rem]"
          >
            {getValue()}
          </span>
        ),
    }),
    columnHelper.accessor('party_1_text', {
      header: `Редакция ${counterpartyRole}`,
      cell: ({ row, getValue }) =>
        editingCell?.rowId === row.original.id && editingCell.field === 'party_1_text' ? (
          <textarea
            autoFocus
            defaultValue={getValue()}
            onBlur={(e) => handleCellBlur(row.original.id, 'party_1_text', getValue(), e.target.value)}
            className="w-full border-none outline-none bg-transparent resize-none"
          />
        ) : (
          <span
            role="cell"
            onClick={() => setEditingCell({ rowId: row.original.id, field: 'party_1_text' })}
            className="cursor-pointer block min-h-[1.5rem] whitespace-pre-wrap"
          >
            {getValue()}
          </span>
        ),
    }),
    columnHelper.accessor('party_2_text', {
      header: `Редакция ${draftingRole}`,
      cell: ({ row, getValue }) =>
        editingCell?.rowId === row.original.id && editingCell.field === 'party_2_text' ? (
          <textarea
            autoFocus
            defaultValue={getValue()}
            onBlur={(e) => handleCellBlur(row.original.id, 'party_2_text', getValue(), e.target.value)}
            className="w-full border-none outline-none bg-transparent resize-none"
          />
        ) : (
          <span
            role="cell"
            onClick={() => setEditingCell({ rowId: row.original.id, field: 'party_2_text' })}
            className="cursor-pointer block min-h-[1.5rem] whitespace-pre-wrap"
          >
            {getValue()}
          </span>
        ),
    }),
    columnHelper.accessor('agreed_text', {
      header: 'Согласованная редакция',
      cell: ({ row, getValue }) =>
        editingCell?.rowId === row.original.id && editingCell.field === 'agreed_text' ? (
          <textarea
            autoFocus
            defaultValue={getValue()}
            onBlur={(e) => handleCellBlur(row.original.id, 'agreed_text', getValue(), e.target.value)}
            className="w-full border-none outline-none bg-transparent resize-none"
          />
        ) : (
          <span
            role="cell"
            onClick={() => setEditingCell({ rowId: row.original.id, field: 'agreed_text' })}
            className="cursor-pointer block min-h-[1.5rem] whitespace-pre-wrap"
          >
            {getValue()}
          </span>
        ),
    }),
    columnHelper.display({
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex gap-1">
          {row.original.confidence < 0.85 && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800" title={`Уверенность: ${row.original.confidence}`}>
              ⚠
            </span>
          )}
          <details className="relative">
            <summary className="cursor-pointer list-none text-gray-400 hover:text-gray-700">⋯</summary>
            <div className="absolute right-0 z-10 bg-white shadow rounded border p-1 flex flex-col gap-1 text-sm">
              <button onClick={() => onMerge(row.original.id, 'previous')}>↑ Объединить с предыдущей</button>
              <button onClick={() => onMerge(row.original.id, 'next')}>↓ Объединить со следующей</button>
              <button className="text-red-500" onClick={() => onDelete(row.original.id)}>✕ Исключить</button>
            </div>
          </details>
        </div>
      ),
    }),
  ]

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row) => row.id,
  })

  return (
    <div>
      <div className="flex gap-2 mb-2">
        <button onClick={onAddRow} className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100">+ Добавить строку</button>
        <button onClick={onSwapParties} className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-100">⇄ Поменять стороны</button>
      </div>
      <table className="w-full border-collapse text-sm">
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th key={h.id} className="border px-2 py-1 bg-gray-50 text-left font-semibold">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className={row.original.flags.includes('manual_review') ? 'bg-yellow-50' : ''}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="border px-2 py-1 align-top">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/app/documents/[id]/protocol/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { AnalysisOut, Protocol, ProtocolRow, ValidationReport } from "@/lib/types";
import ProtocolTable from "@/components/ProtocolTable";

export default function ProtocolPage({ params }: { params: { id: string } }) {
  const [protocol, setProtocol] = useState<Protocol | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Decide between loading existing rows vs first-time build.
    // POST /documents/{id}/protocol wipes-and-rebuilds, which would discard
    // manual edits — so we only call it the first time (no protocol yet).
    //
    // Analysis is fetched AFTER the protocol is built/loaded (not in
    // parallel) so that the validation banner reflects the
    // `validation_report` written by the just-completed build. If we ran
    // them in parallel, the first-build path would render with a stale
    // analysis snapshot and the banner would only appear on a manual
    // refresh.
    (async () => {
      try {
        const existing = await api.listProtocolsForDocument(params.id);
        if (existing.length > 0) {
          // Already built before — load persisted rows without rebuilding.
          const fresh = await api.getProtocolRows(existing[0].id);
          setProtocol(fresh);
        } else {
          // First visit after parties confirmation — build the protocol.
          const built = await api.buildProtocol(params.id);
          setProtocol(built);
        }
        // Fetch analysis AFTER the protocol settles so the validation
        // report (written during build) is visible on first paint.
        try { setAnalysis(await api.getAnalysis(params.id)); } catch { /* non-fatal */ }
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, [params.id]);

  const refreshAnalysis = async () => {
    try { setAnalysis(await api.getAnalysis(params.id)); } catch { /* ignore */ }
  };

  const patch = async (rowId: string, body: Partial<ProtocolRow>) => {
    if (!protocol) return;
    const updated = await api.patchRow(protocol.id, rowId, body);
    setProtocol({ ...protocol, rows: protocol.rows.map((r) => (r.id === rowId ? updated : r)) });
  };

  const merge = async (rowId: string, direction: "previous" | "next") => {
    if (!protocol) return;
    await api.patchRow(protocol.id, rowId, { merge_with: direction });
    // Reload rows after merge — use the read endpoint, NOT buildProtocol,
    // to avoid wiping the just-merged state.
    const fresh = await api.getProtocolRows(protocol.id);
    setProtocol(fresh);
  };

  const remove = async (rowId: string) => {
    if (!protocol) return;
    await api.deleteRow(protocol.id, rowId);
    setProtocol({ ...protocol, rows: protocol.rows.filter((r) => r.id !== rowId) });
  };

  const addRow = async () => {
    if (!protocol) return;
    const created = await api.addRow(protocol.id);
    setProtocol({ ...protocol, rows: [...protocol.rows, created] });
  };

  const swap = async () => {
    if (!protocol) return;
    const updated = await api.swapParties(protocol.id);
    setProtocol(updated);
    await refreshAnalysis();
  };

  if (error) return <main className="p-8 text-red-600">{error}</main>;
  if (!protocol) return <main className="p-8">Строим таблицу…</main>;

  const report: ValidationReport | null = analysis?.validation_report ?? null;
  const uncovered = report ? Math.max(0, report.textual_revisions_total - report.covered_revisions) : 0;
  const warningCount = report?.warnings.length ?? 0;

  return (
    <main className="max-w-7xl mx-auto py-8 px-4 space-y-4">
      <h1 className="text-2xl font-semibold">Протокол разногласий</h1>

      {(uncovered > 0 || warningCount > 0) && (
        <div className="border border-yellow-400 bg-yellow-50 rounded p-3 text-sm space-y-1">
          <div className="font-medium">Проверьте перед экспортом:</div>
          {uncovered > 0 && (
            <div>Не покрыто правок: <strong>{uncovered}</strong> из {report?.textual_revisions_total}.</div>
          )}
          {warningCount > 0 && (
            <ul className="list-disc list-inside">
              {report!.warnings.slice(0, 5).map((w, i) => (
                <li key={i}>{w.message}</li>
              ))}
              {warningCount > 5 && <li>и ещё {warningCount - 5}…</li>}
            </ul>
          )}
        </div>
      )}

      <ProtocolTable
        rows={protocol.rows}
        counterpartyRole={
          analysis?.parties.find((p) => p.id !== analysis?.drafting_party_id)?.role ?? ""
        }
        draftingRole={
          analysis?.parties.find((p) => p.id === analysis?.drafting_party_id)?.role ?? ""
        }
        onPatch={patch}
        onMerge={merge}
        onDelete={remove}
        onAddRow={addRow}
        onSwapParties={swap}
      />

      <button
        onClick={() => router.push(`/documents/${params.id}/export`)}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Экспорт DOCX
      </button>
    </main>
  );
}
```

- [ ] **Step 3: Create `frontend/app/documents/[id]/protocol/__tests__/ProtocolPage.test.tsx`**

Regression test for the analysis re-fetch ordering: on first build the
validation banner must reflect the `validation_report` produced by the
just-completed `buildProtocol()`. If `getAnalysis()` is fired in parallel
with `buildProtocol()` (the previous bug), the analysis snapshot is stale
and warnings appear only after a manual refresh.

```typescript
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../../../../src/mocks/server'
import ProtocolPage from '../page'
import ProtocolTable from '../../../../../components/ProtocolTable'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useParams: () => ({ id: 'doc1' }),
}))

// BASE_ANALYSIS matches AnalysisOut (frontend/lib/types.ts, Task 14):
//   id (not document_id), preflight_metrics (not preflight),
//   validation_report (not validation_summary), contract_name, drafting_party_id.
const BASE_ANALYSIS = {
  id: 'doc1',
  status: 'ready',
  contract_name: null,
  parties: [],
  preflight_metrics: null,
  preflight_diagnostics: [],
  validation_report: null,
  drafting_party_id: null,
}

test('shows validation warnings after first build', async () => {
  let buildDone = false

  server.use(
    // No existing protocol — listProtocolsForDocument returns empty array.
    http.get('/api/protocols', () => HttpResponse.json([])),
    // buildProtocol returns a Protocol shaped as { id, document_id, rows }.
    // ProtocolRow fields: id (not row_id), sort_order, point_label, flags, etc.
    http.post('/api/documents/doc1/protocol', () => {
      buildDone = true
      return HttpResponse.json({
        id: 'p1',
        document_id: 'doc1',
        rows: [{
          id: 'r1',
          sort_order: 0,
          point_label: '1.1',
          party_1_text: 'A',
          party_2_text: 'B',
          agreed_text: 'Редакция Арендатора',
          source_clause_key: null,
          confidence: 0.9,
          flags: ['LOW_NUMBERING_CONFIDENCE'],
          user_edited: false,
        }],
      })
    }),
    // getAnalysis returns warning only after build has completed, proving
    // that the page calls getAnalysis AFTER buildProtocol resolves.
    http.get('/api/documents/doc1/analysis', () =>
      HttpResponse.json({
        ...BASE_ANALYSIS,
        // validation_report.warnings[].kind (not .type) per ValidationWarning type.
        validation_report: buildDone
          ? {
              textual_revisions_total: 1,
              format_only_revisions: 0,
              covered_revisions: 0,
              numbering_confidence_mean: 0.9,
              warnings: [{ kind: 'LOW_NUMBERING_CONFIDENCE', scope: 'row', clause_key: null, row_id: 'r1', message: 'Низкая уверенность нумерации', severity: 'warning' }],
            }
          : null,
      })
    ),
  )

  // ProtocolPage signature: `{ params: { id: string } }` — no documentId prop.
  // The page auto-builds in useEffect (no "Сгенерировать протокол" button),
  // so we wait for a rendered row label to confirm the build completed.
  render(<ProtocolPage params={{ id: 'doc1' }} />)
  // Wait for the row to appear — proves buildProtocol resolved and rows rendered.
  await screen.findByText('1.1')
  // The warning banner must be visible, proving getAnalysis ran AFTER the build.
  await screen.findByText(/Низкая уверенность нумерации/)
})

test('blur without change does not call onPatch', async () => {
  const onPatch = vi.fn()
  render(
    <ProtocolTable
      rows={[{
        id: 'r1', sort_order: 0, point_label: '1.1',
        party_1_text: 'A', party_2_text: 'B', agreed_text: 'Редакция X',
        confidence: 0.95, flags: [], user_edited: false, source_clause_key: null,
      }]}
      draftingRole="Арендатор"
      counterpartyRole="Арендодатель"
      onPatch={onPatch}
      onDelete={vi.fn()}
      onMerge={vi.fn()}
      onAddRow={vi.fn()}
      onSwapParties={vi.fn()}
    />
  )
  const cell = screen.getByText('1.1')
  await userEvent.click(cell)
  const input = screen.getByDisplayValue('1.1')
  await userEvent.tab()  // blur without typing
  expect(onPatch).not.toHaveBeenCalled()
})
```

Note: the `buildDone` flag in the MSW handler closure captures state between the POST and subsequent GET, correctly simulating that getAnalysis called AFTER build returns the fresh validation_report. The second test imports `ProtocolTable` directly (not via `ProtocolPage`) to exercise the no-op blur guard in isolation.

Run: `cd frontend && npm test -- ProtocolPage.test.tsx`
Expected: 2 passed.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npx next build`
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/ProtocolTable.tsx frontend/app/documents/[id]/protocol
git commit -m "feat(frontend): add protocol table with confidence badges, swap, add/exclude/merge rows, and validation banner"
```

---

## Task 18: Export screen

**Files:**
- Create: `frontend/app/documents/[id]/export/page.tsx`

- [ ] **Step 1: Create `frontend/app/documents/[id]/export/page.tsx`**

```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api";

export default function ExportPage({ params }: { params: { id: string } }) {
  const [filename, setFilename] = useState("Протокол разногласий");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sanitize = (raw: string) =>
    raw.trim().replace(/[\\/]/g, "").replace(/[\x00-\x1f\x7f]/g, "").slice(0, 200);

  const submit = async () => {
    const cleaned = sanitize(filename);
    if (!cleaned) { setError("Введите имя файла"); return; }
    setBusy(true);
    setError(null);
    try {
      const blob = await api.exportProtocol(params.id, cleaned);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = cleaned + ".docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="max-w-md mx-auto py-12 px-4 space-y-4">
      <h1 className="text-2xl font-semibold">Экспорт</h1>
      <label className="block">
        <span className="block text-sm mb-1">Имя файла (без .docx)</span>
        <input
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          className="w-full border rounded px-3 py-2"
        />
      </label>
      {error && <p className="text-red-600">{error}</p>}
      <button
        onClick={submit}
        disabled={busy || !sanitize(filename)}
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:bg-gray-300"
      >
        Сохранить
      </button>
    </main>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx next build`
Expected: build succeeds.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/documents/[id]/export
git commit -m "feat(frontend): add export screen with filename sanitization"
```

---

## Task 19: Fixtures + end-to-end integration test

**Files:**
- Modify: `backend/tests/fixtures/builders.py` (add 3 more builders)
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_pipeline_e2e.py`

- [ ] **Step 1: Append new builders to `backend/tests/fixtures/builders.py`**

```python
def build_autonumbering_contract() -> bytes:
    """A contract with manual numeric labels '1.' / '1.1.' / '2.', one INS revision in clause 1.1."""
    doc = DocxDocument()
    doc.add_paragraph("ООО \"Ромашка\", в лице директора, именуемое в дальнейшем \"Арендодатель\", и АО \"Василёк\", именуемое в дальнейшем \"Арендатор\", заключили настоящий договор.")
    doc.add_paragraph("1. Предмет договора")
    p = doc.add_paragraph("1.1. Исполнитель обязуется оказать услуги ")
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1"); ins.set(qn("w:author"), "Editor"); ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t")); t.text = "качественно и в срок"; t.set(qn("xml:space"), "preserve")
    doc.add_paragraph("2. Цена договора")
    buf = BytesIO(); doc.save(buf); return buf.getvalue()


def build_multipar_contract() -> bytes:
    """A clause that spans 2 paragraphs."""
    doc = DocxDocument()
    doc.add_paragraph("ООО \"А\", именуемое в дальнейшем \"Сторона1\", и ООО \"Б\", именуемое в дальнейшем \"Сторона2\".")
    doc.add_paragraph("1. Раздел один")
    p = doc.add_paragraph("Дополнительный текст пункта ")
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1"); ins.set(qn("w:author"), "X"); ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t")); t.text = "ВСТАВКА"; t.set(qn("xml:space"), "preserve")
    buf = BytesIO(); doc.save(buf); return buf.getvalue()


def build_new_clause_contract() -> bytes:
    """A whole paragraph wrapped in <w:ins>."""
    doc = DocxDocument()
    doc.add_paragraph("ООО \"А\", именуемое в дальнейшем \"Сторона1\", и ООО \"Б\", именуемое в дальнейшем \"Сторона2\".")
    doc.add_paragraph("1. Старый пункт")
    p = doc.add_paragraph("")
    pelem = p._p
    ins = etree.SubElement(pelem, qn("w:ins"))
    ins.set(qn("w:id"), "1"); ins.set(qn("w:author"), "X"); ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(ins, qn("w:r"))
    t = etree.SubElement(r, qn("w:t")); t.text = "2. Совершенно новый пункт"; t.set(qn("xml:space"), "preserve")
    buf = BytesIO(); doc.save(buf); return buf.getvalue()


def build_deleted_clause_contract() -> bytes:
    """A whole paragraph wrapped in <w:del>."""
    doc = DocxDocument()
    doc.add_paragraph("ООО \"А\", именуемое в дальнейшем \"Сторона1\", и ООО \"Б\", именуемое в дальнейшем \"Сторона2\".")
    doc.add_paragraph("1. Остающийся пункт")
    p = doc.add_paragraph("")
    pelem = p._p
    deln = etree.SubElement(pelem, qn("w:del"))
    deln.set(qn("w:id"), "1"); deln.set(qn("w:author"), "X"); deln.set(qn("w:date"), "2026-01-01T00:00:00Z")
    r = etree.SubElement(deln, qn("w:r"))
    t = etree.SubElement(r, qn("w:delText")); t.text = "2. Удаляемый пункт целиком"; t.set(qn("xml:space"), "preserve")
    buf = BytesIO(); doc.save(buf); return buf.getvalue()


def build_simple_contract_with_revision() -> bytes:
    return build_docx_with_insertion(
        "ООО \"А\", именуемое в дальнейшем \"Сторона1\", и ООО \"Б\", именуемое в дальнейшем \"Сторона2\". 1. Услуги оказываются ",
        "вовремя",
        ".",
    )
```

- [ ] **Step 2: Create `backend/tests/integration/__init__.py`** (empty)

```python
```

- [ ] **Step 3: Write end-to-end integration test `backend/tests/integration/test_pipeline_e2e.py`**

```python
from io import BytesIO
from docx import Document

from app.services.ingestion import run_pipeline
from app.services.protocol_generator import ProtocolRowBuilder, BuildContext
from app.services.exporter import ProtocolExporter
from app.processing.changed_clause_detector import ChangedClauseDetector
from tests.fixtures.builders import (
    build_simple_contract_with_revision,
    build_autonumbering_contract,
    build_multipar_contract,
    build_new_clause_contract,
    build_deleted_clause_contract,
)


def _full_run(data: bytes, drafting_role: str, counterparty_role: str):
    pipeline = run_pipeline(data)
    changed = ChangedClauseDetector().detect(pipeline["clauses"])
    rows = ProtocolRowBuilder().build(
        changed,
        BuildContext(drafting_party_role=drafting_role, counterparty_role=counterparty_role),
    )
    docx_bytes = ProtocolExporter().export(
        [{"point_label": r.point_label, "party_1_text": r.party_1_text,
          "party_2_text": r.party_2_text, "agreed_text": r.agreed_text} for r in rows],
        drafting_role, counterparty_role, "Договор",
    )
    return rows, docx_bytes


def test_simple_contract_yields_one_row_and_valid_docx():
    rows, data = _full_run(build_simple_contract_with_revision(), "Сторона2", "Сторона1")
    assert len(rows) == 1
    doc = Document(BytesIO(data))
    assert len(doc.tables) == 1
    assert len(doc.tables[0].rows) == 2  # header + 1 row


def test_autonumbering_contract_pipeline():
    rows, _ = _full_run(build_autonumbering_contract(), "Арендатор", "Арендодатель")
    assert any(r.point_label.startswith("1.1") for r in rows)


def test_multipar_contract_keeps_continuation():
    rows, _ = _full_run(build_multipar_contract(), "Сторона2", "Сторона1")
    # The INSERT lives in the continuation paragraph attached to clause 1.
    assert any("ВСТАВКА" in r.party_2_text for r in rows)


def test_new_clause_contract_produces_new_pungkt_label():
    rows, _ = _full_run(build_new_clause_contract(), "Сторона2", "Сторона1")
    new_rows = [r for r in rows if r.point_label.startswith("Новый пункт")]
    assert len(new_rows) >= 1
    assert new_rows[0].party_1_text == "—"


def test_deleted_clause_contract_produces_exclude_text():
    rows, _ = _full_run(build_deleted_clause_contract(), "Сторона2", "Сторона1")
    excl = [r for r in rows if r.party_2_text.startswith("Исключить пункт")]
    assert len(excl) >= 1
```

- [ ] **Step 4: Run the integration tests**

Run: `cd backend && pytest tests/integration -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full test suite**

Run: `cd backend && pytest -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/fixtures/builders.py backend/tests/integration
git commit -m "test(integration): add 5 fixture-based pipeline end-to-end tests"
```

---

## Self-review notes

The plan was reviewed against the spec for coverage, placeholders, and type consistency. Adjustments made inline:

- **Spec coverage**: tasks cover all listed requirements: ingestion (Task 10), revision pipeline (Tasks 1–5), party extraction (Task 6), row building (Task 7), validation (Task 8), upload (Task 10), analysis + parties (Task 11), build + edit + add/delete row + swap parties (Task 12), export + raw download (Task 13), all five UI screens including confidence badges, swap-parties button, add/exclude/merge row actions, and validation banner (Tasks 15–18), fixtures + e2e (Task 19). Tables are handled end-to-end: parsed as `RawTable` with rows/cells (Task 1), attached to enclosing clauses by `ClauseSegmenter` or marked `STANDALONE_TABLE` (Task 4), rendered into rows with `TABLE_CELL_CHANGE` flag (Task 7), and standalone tables produce a `point_label="Таблица"` row with `manual_review` flag for human review (per spec §5.9). Spec features intentionally out of MVP (mammoth.js preview, structured table-cell-level revision diffs, undo/redo) are deferred.
- **Placeholders**: every step contains either real code, a real shell command with expected outcome, or a real test. No "TBD" / "implement later" remains.
- **Type consistency**: the dataclass surface in `processing/types.py` is consumed identically by every downstream module — `RawDocument`, `RawParagraph`, `RawTable`, `RawTableRow`, `RawTableCell`, `RevisionData`, `RevisionRecord`, `NumberingData`, `EnrichedParagraph`, `Clause` (with `paragraphs` and `tables` fields). The DB models (`Document`, `Party`, `Clause`, `Protocol`, `ProtocolRow`) match the JSON shapes returned by the API schemas. `BuiltRow` produced by `ProtocolRowBuilder` (Task 7) matches the columns persisted in `ProtocolRow` (Task 12) and exported in `ProtocolExporter` (Task 13). Frontend `ProtocolRow` type (Task 14) mirrors backend response shape (Task 12); the new endpoints (`POST /protocols/{pid}/rows`, `DELETE /protocols/{pid}/rows/{rid}`, `POST /protocols/{pid}/swap-parties`, and `merge_with` PATCH directive) have matching client methods (`addRow`, `deleteRow`, `swapParties`, extended `patchRow`). Function names `OOXMLParser.parse`, `RevisionResolver.resolve(data, raw) -> (mapping, list[ResolverDiagnostic])`, `NumberingResolver.resolve(data, raw) -> (mapping, list[ResolverDiagnostic])`, `ClauseSegmenter.segment(blocks)`, `ChangedClauseDetector.detect(clauses)`, `ProtocolRowBuilder.build(clauses, ctx)`, `ValidationEngine.validate(protocol_rows, all_clauses, resolver_diagnostics)`, `ProtocolExporter.export(rows, drafting_role, counterparty_role, contract_name)` are used consistently across tasks. `ResolverDiagnostic` (defined in Task 1's `processing/types.py`) is emitted by the revision/numbering resolvers in Tasks 2–3, aggregated in `run_pipeline` in Task 10, persisted on `Document.metadata_json`, and surfaced through `AnalysisOut.preflight_diagnostics` in Task 11. Tables flow through the same diagnostic-free path: `RawTable` from Task 1 → attached to clause by `ClauseSegmenter` (Task 4) → forced into `changed_clauses` when `has_revisions` or `STANDALONE_TABLE` (Task 5) → persisted via `ClauseModel.tables_json` (Tasks 1/10) → rehydrated and rendered by `ProtocolRowBuilder` on rebuild (Task 12). Swap-parties (Task 12) preserves the column-2/column-3 invariant: it only flips `Document.drafting_party_id` and recomputes `agreed_text` for rows where `user_edited == False`, leaving any user-edited row untouched; column header labels are derived on the frontend from the parties+drafting role at render time (Task 17).
- **Known simplifications versus full spec**: this MVP uses Postgres/Celery/MinIO per the user's task brief instead of the spec's SQLite/no-queue/local-FS distribution model; a custom `RevisionResolver` walks the OOXML directly rather than wrapping `docx-revisions` (the dataclass surface stays compatible so a swap is local to one file); `mammoth.js` preview, structured table-cell-level revision diffs, and TanStack Query data fetching are intentionally deferred. These are acknowledged trade-offs against the spec, not silent omissions.
