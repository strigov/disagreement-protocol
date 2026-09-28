import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from tests.fixtures.builders import build_simple_docx


@pytest.mark.asyncio
async def test_upload_rejects_non_docx_extension():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/documents",
            files={"file": ("a.txt", b"hi", "text/plain")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_corrupted_zip():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/documents",
            files={"file": ("a.docx", b"not-a-zip", "application/octet-stream")},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file_without_side_effects(monkeypatch):
    calls = []

    class FakeDb:
        def add(self, obj):
            calls.append(("db.add", obj))

        def commit(self):
            calls.append(("db.commit",))

    def override_get_db():
        yield FakeDb()

    class FakeStorage:
        def put(self, key, body):
            calls.append(("storage.put", key, body))

    def fake_process(document_id):
        calls.append(("background.process", document_id))

    monkeypatch.setattr("app.api.documents.MAX_BYTES", 16, raising=False)
    monkeypatch.setattr("app.api.documents.FileStorage", FakeStorage)
    monkeypatch.setattr("app.api.documents.process_document", fake_process)
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
            response = await client.post(
                "/api/documents",
                files={
                    "file": (
                        "large.docx",
                        b"x" * 17,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert calls == []


@pytest.mark.asyncio
async def test_upload_happy_path_creates_document(monkeypatch):
    data = build_simple_docx(["hello"])
    captured = {}

    class FakeDb:
        def add(self, obj):
            captured["document"] = obj

        def commit(self):
            captured["committed"] = True

    def override_get_db():
        yield FakeDb()

    class FakeStorage:
        def put(self, key, body):
            captured["key"] = key
            captured["len"] = len(body)

    def fake_process(document_id):
        captured["task_doc_id"] = document_id

    monkeypatch.setattr("app.api.documents.FileStorage", FakeStorage)
    monkeypatch.setattr("app.api.documents.process_document", fake_process)
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
            response = await client.post(
                "/api/documents",
                files={
                    "file": (
                        "contract.docx",
                        data,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "uploaded"
    assert uuid.UUID(body["id"])
    assert captured["document"].id == uuid.UUID(body["id"])
    assert captured["document"].original_filename == "contract.docx"
    assert captured["document"].contract_name == "contract"
    assert captured["key"] == f"documents/{body['id']}/input.docx"
    assert captured["len"] == len(data)
    assert captured["task_doc_id"] == body["id"]
    assert captured["committed"] is True
