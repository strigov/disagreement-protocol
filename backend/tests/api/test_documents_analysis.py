import uuid
from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party


class FakeQuery:
    def __init__(self, rows: list[Party]) -> None:
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self) -> list[Party]:
        return list(self.rows)


class FakeDb:
    def __init__(self, doc: Document, parties: list[Party]) -> None:
        self.doc = doc
        self.parties = parties
        self.committed = False

    def get(self, model, obj_id):
        if model is Document and obj_id == self.doc.id:
            return self.doc
        return None

    def query(self, model):
        assert model is Party
        return FakeQuery(self.parties)

    def add(self, obj) -> None:
        if isinstance(obj, Party):
            if obj.id is None:
                obj.id = uuid.uuid4()
            self.parties.append(obj)

    def delete(self, obj) -> None:
        if obj in self.parties:
            self.parties.remove(obj)

    def commit(self) -> None:
        self.committed = True


@pytest.fixture
def parsed_doc() -> tuple[Document, Party, FakeDb]:
    doc = Document(
        id=uuid.uuid4(),
        original_filename="t.docx",
        storage_key="t/k",
        contract_name="t",
        status=DocumentStatus.PARSED,
        preflight_metrics={
            "revisions_total": 1,
            "format_only_count": 0,
            "paragraphs_with_numbering": 1,
            "numbering_confidence_mean": 1.0,
        },
        metadata_json={
            "preflight_diagnostics": [
                {
                    "level": "warning",
                    "component": "numbering",
                    "code": "UNKNOWN_NUMID",
                    "message": "numId 999 not found in numbering.xml",
                    "block_id": "p_0001",
                },
            ]
        },
    )
    party = Party(
        id=uuid.uuid4(),
        document_id=doc.id,
        name="ООО Ромашка",
        role="Арендодатель",
        confidence=0.9,
    )
    db = FakeDb(doc, [party])
    return doc, party, db


@pytest.fixture
def override_db(parsed_doc: tuple[Document, Party, FakeDb]) -> Iterator[FakeDb]:
    _, _, db = parsed_doc

    def dependency_override() -> Iterator[FakeDb]:
        yield db

    app.dependency_overrides[get_db] = dependency_override
    try:
        yield db
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_analysis_returns_parties(parsed_doc, override_db):
    doc, _, _ = parsed_doc
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/documents/{doc.id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["contract_name"] == "t"
    assert body["error_message"] is None
    assert len(body["parties"]) == 1
    assert body["parties"][0]["role"] == "Арендодатель"


@pytest.mark.asyncio
async def test_get_analysis_returns_saved_error_message_for_failed_document(
    parsed_doc,
    override_db,
):
    doc, _, _ = parsed_doc
    doc.status = DocumentStatus.FAILED
    doc.error_message = "Ошибка разбора OOXML: недопустимый XML-узел"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/documents/{doc.id}/analysis")

    assert response.status_code == 200
    assert response.json()["error_message"] == (
        "Ошибка разбора OOXML: недопустимый XML-узел"
    )


@pytest.mark.asyncio
async def test_get_analysis_includes_preflight_diagnostics(parsed_doc, override_db):
    doc, _, _ = parsed_doc
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/documents/{doc.id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert "preflight_diagnostics" in body
    assert len(body["preflight_diagnostics"]) == 1
    diagnostic = body["preflight_diagnostics"][0]
    assert diagnostic["component"] == "numbering"
    assert "numId 999" in diagnostic["message"]


@pytest.mark.asyncio
async def test_get_analysis_includes_validation_report_warnings(parsed_doc, override_db):
    doc, _, _ = parsed_doc
    doc.validation_report = {
        "textual_revisions_total": 1,
        "format_only_revisions": 0,
        "covered_revisions": 1,
        "numbering_confidence_mean": 1.0,
        "warnings": [
            {
                "kind": "NUMBERING_MAPPING_MISMATCH",
                "scope": "session",
                "severity": "warning",
                "component": "numbering",
                "block_id": "p_0001",
                "message": "numId 999 not found in numbering.xml",
            },
        ],
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/documents/{doc.id}/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["validation_report"] is not None
    kinds = [warning["kind"] for warning in body["validation_report"]["warnings"]]
    assert "NUMBERING_MAPPING_MISMATCH" in kinds


@pytest.mark.asyncio
async def test_patch_parties_sets_drafting_and_status(parsed_doc, override_db):
    doc, party, db = parsed_doc
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"id": str(party.id), "name": "ООО Ромашка", "role": "Арендодатель"},
                    {"name": "АО Василёк", "role": "Арендатор"},
                ],
                "drafting_party_id": str(party.id),
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["drafting_party_id"] == str(party.id)
    assert body["status"] == "parties_confirmed"
    assert body["error_message"] is None
    assert len(body["parties"]) == 2
    assert db.committed is True


@pytest.mark.asyncio
async def test_patch_parties_creates_new_party_when_payload_item_has_no_id_even_if_name_matches_existing(
    parsed_doc,
    override_db,
):
    doc, party, db = parsed_doc

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"name": party.name, "role": "Арендатор"},
                    {"id": str(party.id), "name": "ООО Ромашка-1", "role": "Арендодатель"},
                ],
                "drafting_party_id": str(party.id),
            },
        )

    assert response.status_code == 200, response.text
    assert len(db.parties) == 2
    existing_party = next(saved for saved in db.parties if saved.id == party.id)
    new_party = next(saved for saved in db.parties if saved.id != party.id)
    assert (existing_party.name, existing_party.role) == ("ООО Ромашка-1", "Арендодатель")
    assert (new_party.name, new_party.role) == ("ООО Ромашка", "Арендатор")


@pytest.mark.asyncio
async def test_patch_parties_clears_drafting_party_when_payload_null(parsed_doc, override_db):
    doc, party_a, db = parsed_doc
    party_b = Party(
        id=uuid.uuid4(),
        document_id=doc.id,
        name="АО Василёк",
        role="Арендатор",
        confidence=0.8,
    )
    db.parties.append(party_b)
    doc.drafting_party_id = party_a.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"id": str(party_b.id), "name": "АО Василёк", "role": "Арендатор"},
                    {"name": "ООО Лютик", "role": "Поручитель"},
                ],
                "drafting_party_id": None,
            },
        )

    assert response.status_code == 200, response.text
    assert doc.drafting_party_id is None
    assert party_a not in db.parties
    assert db.committed is True


@pytest.mark.asyncio
async def test_patch_parties_rejects_duplicate_existing_party_ids_without_db_changes(parsed_doc, override_db):
    doc, party, db = parsed_doc
    original_status = doc.status
    original_drafting_party_id = doc.drafting_party_id
    original_party_state = (party.id, party.name, party.role, party.confidence)
    original_parties = list(db.parties)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"id": str(party.id), "name": "ООО Ромашка", "role": "Арендодатель"},
                    {"id": str(party.id), "name": "АО Василёк", "role": "Арендатор"},
                ],
                "drafting_party_id": None,
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Duplicate party ids in payload"}
    assert doc.status == original_status
    assert doc.drafting_party_id == original_drafting_party_id
    assert (party.id, party.name, party.role, party.confidence) == original_party_state
    assert db.parties == original_parties
    assert db.committed is False


@pytest.mark.asyncio
async def test_patch_parties_rejects_empty_parties_without_db_changes(parsed_doc, override_db):
    doc, party, db = parsed_doc
    original_status = doc.status
    original_parties = list(db.parties)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={"parties": [], "drafting_party_id": None},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Exactly 2 parties are required"}
    assert doc.status == original_status
    assert db.parties == original_parties
    assert party in db.parties
    assert db.committed is False


@pytest.mark.asyncio
async def test_patch_parties_rejects_unknown_drafting_party_without_db_changes(parsed_doc, override_db):
    doc, party, db = parsed_doc
    original_status = doc.status
    original_drafting_party_id = doc.drafting_party_id
    original_parties = list(db.parties)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"id": str(party.id), "name": "ООО Ромашка", "role": "Арендодатель"},
                    {"name": "АО Василёк", "role": "Арендатор"},
                ],
                "drafting_party_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "drafting_party_id must reference one of the confirmed parties"}
    assert doc.status == original_status
    assert doc.drafting_party_id == original_drafting_party_id
    assert db.parties == original_parties
    assert db.committed is False


@pytest.mark.asyncio
async def test_patch_parties_rejects_drafting_party_id_when_payload_only_matches_name(parsed_doc, override_db):
    doc, party_a, db = parsed_doc
    party_b = Party(
        id=uuid.uuid4(),
        document_id=doc.id,
        name=party_a.name,
        role="Арендатор",
        confidence=0.8,
    )
    db.parties.append(party_b)
    original_status = doc.status
    original_drafting_party_id = doc.drafting_party_id
    original_parties = list(db.parties)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"id": str(party_b.id), "name": party_b.name, "role": "Арендатор"},
                    {"name": "АО Василёк", "role": "Арендодатель"},
                ],
                "drafting_party_id": str(party_a.id),
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "drafting_party_id must reference one of the confirmed parties"}
    assert doc.status == original_status
    assert doc.drafting_party_id == original_drafting_party_id
    assert db.parties == original_parties
    assert db.committed is False


@pytest.mark.asyncio
async def test_patch_parties_rejects_payload_id_for_new_drafting_party_without_db_changes(parsed_doc, override_db):
    doc, party, db = parsed_doc
    original_status = doc.status
    original_drafting_party_id = doc.drafting_party_id
    original_parties = list(db.parties)
    client_supplied_new_party_id = uuid.uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/documents/{doc.id}/parties",
            json={
                "parties": [
                    {"id": str(party.id), "name": "ООО Ромашка", "role": "Арендодатель"},
                    {
                        "id": str(client_supplied_new_party_id),
                        "name": "АО Василёк",
                        "role": "Арендатор",
                    },
                ],
                "drafting_party_id": str(client_supplied_new_party_id),
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "drafting_party_id must reference one of the confirmed parties"}
    assert doc.status == original_status
    assert doc.drafting_party_id == original_drafting_party_id
    assert db.parties == original_parties
    assert db.committed is False
