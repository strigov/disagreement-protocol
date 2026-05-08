import configparser
from pathlib import Path


def test_settings_use_defaults_and_environment_overrides(monkeypatch):
    from app.config import Settings, get_settings

    get_settings.cache_clear()
    defaults = Settings()
    assert defaults.database_url == "postgresql+psycopg://disprot:disprot@localhost:5432/disprot"
    assert defaults.redis_url == "redis://localhost:6379/0"
    assert defaults.s3_bucket == "disprot"
    assert defaults.app_env == "local"

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/test")
    overridden = Settings()
    assert overridden.database_url == "postgresql+psycopg://user:pass@db:5432/test"


def test_models_register_expected_bootstrap_tables_and_columns():
    import app.models  # noqa: F401
    from app.db.base import Base
    from app.models.enums import DocumentStatus

    assert {status.value for status in DocumentStatus} == {
        "uploaded",
        "parsing",
        "parsed",
        "parties_confirmed",
        "built",
        "exported",
        "failed",
    }

    assert set(Base.metadata.tables) == {
        "documents",
        "parties",
        "clauses",
        "protocols",
        "protocol_rows",
    }

    documents = Base.metadata.tables["documents"]
    assert documents.c.status.type.name == "document_status"
    assert documents.c.original_filename.type.length == 512
    assert documents.c.error_message.type.length == 2048

    clauses = Base.metadata.tables["clauses"]
    assert "document_id" in clauses.c
    assert "flags" in clauses.c
    assert "tables_json" in clauses.c

    protocol_rows = Base.metadata.tables["protocol_rows"]
    assert "protocol_id" in protocol_rows.c
    assert "user_edited" in protocol_rows.c


def test_local_dev_configuration_exposes_required_services():
    root = Path(__file__).resolve().parents[2]

    env_values = dict(
        line.split("=", 1)
        for line in (root / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert env_values == {
        "DATABASE_URL": "postgresql+psycopg://disprot:disprot@localhost:5432/disprot",
        "REDIS_URL": "redis://localhost:6379/0",
        "S3_ENDPOINT": "http://localhost:9000",
        "S3_ACCESS_KEY": "disprot",
        "S3_SECRET_KEY": "disprotsecret",
        "S3_BUCKET": "disprot",
        "APP_ENV": "local",
    }

    alembic_ini = configparser.ConfigParser()
    alembic_ini.read(root / "backend" / "alembic.ini")
    assert alembic_ini["alembic"]["script_location"] == "alembic"
    assert (
        alembic_ini["alembic"]["sqlalchemy.url"]
        == "postgresql+psycopg://disprot:disprot@localhost:5432/disprot"
    )
