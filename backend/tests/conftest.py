import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch, tmp_path):
    """Test startup/recovery must never read or change the user's local database."""
    import app.models  # noqa: F401
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db.base import Base
    from types import SimpleNamespace

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr("app.db.session.engine", engine)
    monkeypatch.setattr("app.db.session.SessionLocal", session_factory)
    monkeypatch.setattr("app.services.processing.SessionLocal", session_factory)
    monkeypatch.setattr("app.services.storage.get_settings", lambda: SimpleNamespace(storage_dir=str(tmp_path / "files")))
    yield session_factory
    engine.dispose()
