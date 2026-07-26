from pathlib import Path


def test_settings_use_defaults_and_environment_overrides(monkeypatch):
    from app.config import Settings, get_settings

    get_settings.cache_clear()
    defaults = Settings()
    assert defaults.database_url == "sqlite:///./data/disprot.db"
    assert defaults.storage_dir == "./data/files"
    assert defaults.app_env == "local"

    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/other.db")
    monkeypatch.setenv("STORAGE_DIR", "/tmp/other-files")
    overridden = Settings()
    assert overridden.database_url == "sqlite:////tmp/other.db"
    assert overridden.storage_dir == "/tmp/other-files"


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
    assert "paragraphs_json" in clauses.c
    assert "tables_json" in clauses.c

    protocol_rows = Base.metadata.tables["protocol_rows"]
    assert "protocol_id" in protocol_rows.c
    assert "user_edited" in protocol_rows.c


def test_schema_creates_on_sqlite_in_memory():
    """The whole schema must be creatable on SQLite (the only supported engine)."""
    from sqlalchemy import create_engine

    import app.models  # noqa: F401
    from app.db.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Base.metadata.drop_all(engine)


def test_env_example_matches_local_stack():
    root = Path(__file__).resolve().parents[2]

    env_values = dict(
        line.split("=", 1)
        for line in (root / ".env.example").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert env_values == {
        "DATABASE_URL": "sqlite:///./data/disprot.db",
        "STORAGE_DIR": "./data/files",
        "APP_ENV": "local",
    }
