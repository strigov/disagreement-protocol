import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.main import create_app

TOKEN = "a" * 64


@pytest.mark.parametrize("token", [None, "wrong", "b" * 64])
def test_desktop_rejects_other_local_clients(token):
    with TestClient(create_app(desktop_token=TOKEN), base_url="http://127.0.0.1") as client:
        headers = {"x-disprot-token": token} if token else {}
        assert client.get("/health", headers=headers).status_code == 403
        assert client.post("/api/documents", headers=headers, content=b"invalid").status_code == 403


def test_desktop_only_accepts_its_own_origin():
    with TestClient(create_app(desktop_token=TOKEN), base_url="http://127.0.0.1") as client:
        headers = {"x-disprot-token": TOKEN, "origin": "disprot://app"}
        assert client.get("/health", headers=headers).json() == {"status": "ok"}
        for origin in ("http://localhost:3000", "https://example.com", "null"):
            assert client.get("/health", headers={**headers, "origin": origin}).status_code == 403


def test_desktop_data_path_ignores_developer_configuration(monkeypatch, tmp_path):
    root = tmp_path / "Данные юриста с пробелами"
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DATABASE_URL=sqlite:///unwanted.db\nSTORAGE_DIR=unwanted", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///also-unwanted.db")
    monkeypatch.setenv("STORAGE_DIR", "also-unwanted")
    monkeypatch.setenv("DISPROT_DATA_DIR", str(root))
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert make_url(settings.database_url).database == str(root / "disprot.db")
        assert settings.storage_dir == str(root / "files")
        assert settings.app_env == "desktop"
    finally:
        get_settings.cache_clear()
