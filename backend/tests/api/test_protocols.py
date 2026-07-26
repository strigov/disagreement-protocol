import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.clause import Clause as ClauseModel
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.models.protocol import Protocol, ProtocolRow
from app.services.protocol_generator import ProtocolRowBuilder


class FakeQuery:
    def __init__(self, db: "FakeDb", model) -> None:
        self.db = db
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        if self.model is Party:
            return list(self.db.parties)
        if self.model is ClauseModel:
            return sorted(self.db.clauses, key=lambda clause: clause.sort_order)
        if self.model is Protocol:
            return list(self.db.protocols)
        if self.model is ProtocolRow:
            return sorted(self.db.rows, key=lambda row: row.sort_order)
        if self.model is Protocol.id:
            return list(self.db.protocols)
        return []

    def delete(self, synchronize_session=None):
        if self.model is ProtocolRow:
            count = len(self.db.rows)
            self.db.rows.clear()
            return count
        if self.model is Protocol:
            count = len(self.db.protocols)
            self.db.protocols.clear()
            return count
        return 0


class FakeScalarResult:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDb:
    def __init__(self, doc: Document, parties: list[Party], clauses: list[ClauseModel]) -> None:
        self.doc = doc
        self.parties = parties
        self.clauses = clauses
        self.protocols: list[Protocol] = []
        self.rows: list[ProtocolRow] = []

    def add(self, obj) -> None:
        if isinstance(obj, Document):
            self.doc = obj
        elif isinstance(obj, Party):
            if obj.id is None:
                obj.id = uuid.uuid4()
            self.parties.append(obj)
        elif isinstance(obj, ClauseModel):
            if obj.id is None:
                obj.id = uuid.uuid4()
            self.clauses.append(obj)
        elif isinstance(obj, Protocol):
            if obj.id is None:
                obj.id = uuid.uuid4()
            self.protocols.append(obj)
        elif isinstance(obj, ProtocolRow):
            if obj.id is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    def add_all(self, objects) -> None:
        for obj in objects:
            self.add(obj)

    def flush(self) -> None:
        for collection in (self.parties, self.clauses, self.protocols, self.rows):
            for obj in collection:
                if obj.id is None:
                    obj.id = uuid.uuid4()

    def commit(self) -> None:
        self.flush()

    def close(self) -> None:
        pass

    def delete(self, obj) -> None:
        for collection in (self.parties, self.clauses, self.protocols, self.rows):
            if obj in collection:
                collection.remove(obj)
                return

    def get(self, model, obj_id):
        if model is Document and obj_id == self.doc.id:
            return self.doc
        if model is Protocol:
            return next((protocol for protocol in self.protocols if protocol.id == obj_id), None)
        if model is ProtocolRow:
            return next((row for row in self.rows if row.id == obj_id), None)
        return None

    def execute(self, statement):
        # The API tests do not model database row locks; they only exercise
        # build_protocol's SELECT ... FOR UPDATE path with the fake document.
        return FakeScalarResult(self.doc)

    def query(self, model):
        return FakeQuery(self, model)


@pytest.fixture
def doc_with_changes() -> Iterator[tuple[Document, Party, Party]]:
    doc = Document(
        id=uuid.uuid4(),
        original_filename="t.docx",
        storage_key="k",
        contract_name="Договор",
        status=DocumentStatus.PARTIES_CONFIRMED,
        preflight_metrics={
            "revisions_total": 1,
            "format_only_count": 0,
            "paragraphs_with_numbering": 1,
            "numbering_confidence_mean": 1.0,
        },
    )
    p1 = Party(id=uuid.uuid4(), document_id=doc.id, name="ООО Ромашка", role="Арендодатель", confidence=0.9)
    p2 = Party(id=uuid.uuid4(), document_id=doc.id, name="АО Василёк", role="Арендатор", confidence=0.9)
    doc.drafting_party_id = p2.id
    clause = ClauseModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        clause_key="c_p_0001",
        label="1.",
        level=0,
        parent_key=None,
        sort_order=0,
        original_text="Старый",
        accepted_text="Новый",
        flags=[],
        confidence=1.0,
        revisions=[{"type": "INS", "text": "Новый", "author": ""}],
    )
    db = FakeDb(doc, [p1, p2], [clause])

    def dependency_override() -> Iterator[FakeDb]:
        yield db

    app.dependency_overrides[get_db] = dependency_override
    try:
        yield doc, p1, p2
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def doc_with_versioned_table_cells() -> Iterator[Document]:
    doc = Document(
        id=uuid.uuid4(),
        original_filename="table.docx",
        storage_key="table-key",
        contract_name="Договор",
        status=DocumentStatus.PARTIES_CONFIRMED,
        preflight_metrics={
            "revisions_total": 2,
            "format_only_count": 0,
            "paragraphs_with_numbering": 1,
            "numbering_confidence_mean": 1.0,
        },
    )
    p1 = Party(id=uuid.uuid4(), document_id=doc.id, name="ООО Ромашка", role="Арендодатель", confidence=0.9)
    p2 = Party(id=uuid.uuid4(), document_id=doc.id, name="АО Василёк", role="Арендатор", confidence=0.9)
    doc.drafting_party_id = p2.id
    clause = ClauseModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        clause_key="c_p_0001",
        label="1.",
        level=0,
        parent_key=None,
        sort_order=0,
        original_text="",
        accepted_text="",
        flags=[],
        confidence=1.0,
        revisions=[
            {"type": "DEL", "text": "1 200", "author": "Юрист"},
            {"type": "INS", "text": "1 100", "author": "Юрист"},
        ],
        tables_json=[
            {
                "block_id": "t_0001",
                "has_revisions": True,
                "rows": [
                    [
                        {
                            "original_text": "2026 год",
                            "accepted_text": "2026 год",
                            "revisions": [],
                        },
                        {
                            "original_text": "1 200",
                            "accepted_text": "1 100",
                            "revisions": [
                                {"type": "DEL", "text": "1 200", "author": "Юрист"},
                                {"type": "INS", "text": "1 100", "author": "Юрист"},
                            ],
                        },
                        "192 500",
                    ],
                    ["legacy cell"],
                ],
            },
        ],
    )
    db = FakeDb(doc, [p1, p2], [clause])

    def dependency_override() -> Iterator[FakeDb]:
        yield db

    app.dependency_overrides[get_db] = dependency_override
    try:
        yield doc
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def doc_with_paragraph_payload() -> Iterator[tuple[Document, FakeDb]]:
    doc = Document(
        id=uuid.uuid4(),
        original_filename="annex.docx",
        storage_key="annex-key",
        contract_name="Договор",
        status=DocumentStatus.PARTIES_CONFIRMED,
    )
    p1 = Party(id=uuid.uuid4(), document_id=doc.id, name="ООО Ромашка", role="Арендодатель", confidence=0.9)
    p2 = Party(id=uuid.uuid4(), document_id=doc.id, name="АО Василёк", role="Арендатор", confidence=0.9)
    doc.drafting_party_id = p2.id
    clause = ClauseModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        clause_key="c_p_0007",
        label="Приложение № 1",
        level=0,
        parent_key=None,
        sort_order=0,
        original_text="Старое\nПродолжение",
        accepted_text="Новое\nПродолжение",
        flags=[],
        confidence=0.99,
        revisions=[],
        paragraphs_json=[
            {
                "block_id": "p_0007",
                "text_runs": "Старое",
                "num_id": 1,
                "ilvl": 0,
                "original_text": "Старое",
                "accepted_text": "Новое",
                "revisions": [
                    {"type": "DEL", "text": "Старое", "author": "Юрист"},
                    {"type": "INS", "text": "Новое", "author": "Юрист"},
                ],
                "rendered_number": "1.",
                "numbering_confidence": 0.8,
                "numbering_level": 0,
            },
            {
                "block_id": "p_0008",
                "text_runs": "Продолжение",
                "num_id": 1,
                "ilvl": 1,
                "original_text": "Продолжение",
                "accepted_text": "Продолжение",
                "revisions": [],
                "rendered_number": "1.1.",
                "numbering_confidence": 0.6,
                "numbering_level": 1,
            },
        ],
    )
    second_clause = ClauseModel(
        id=uuid.uuid4(),
        document_id=doc.id,
        clause_key="c_p_0009",
        label="2.",
        level=0,
        parent_key=None,
        sort_order=1,
        original_text="Без изменений",
        accepted_text="Без изменений",
        flags=[],
        confidence=0.4,
        revisions=[],
        paragraphs_json=[
            {
                "block_id": "p_0009",
                "text_runs": "Без изменений",
                "num_id": 1,
                "ilvl": 0,
                "original_text": "Без изменений",
                "accepted_text": "Без изменений",
                "revisions": [],
                "rendered_number": "2.",
                "numbering_confidence": 0.4,
                "numbering_level": 0,
            },
        ],
    )
    db = FakeDb(doc, [p1, p2], [clause, second_clause])

    def dependency_override() -> Iterator[FakeDb]:
        yield db

    app.dependency_overrides[get_db] = dependency_override
    try:
        yield doc, db
    finally:
        app.dependency_overrides.clear()


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


def test_build_protocol_round_trips_versioned_and_legacy_table_cells(doc_with_versioned_table_cells):
    with TestClient(app) as client:
        response = client.post(f"/api/documents/{doc_with_versioned_table_cells.id}/protocol")

    assert response.status_code == 201, response.text
    row = response.json()["rows"][0]
    assert row["party_1_text"] == "2026 год | 1 200 | 192 500\nlegacy cell"
    assert row["party_2_text"] == "2026 год | 1 100 | 192 500\nlegacy cell"
    assert "1 2001 100" not in row["party_1_text"] + row["party_2_text"]
    assert "TABLE_CELL_CHANGE" in row["flags"]


def test_build_protocol_restores_paragraph_payload_and_exact_confidence_mean(
    doc_with_paragraph_payload,
    monkeypatch,
):
    doc, _ = doc_with_paragraph_payload
    captured_clauses = []
    original_build = ProtocolRowBuilder.build

    def capture_build(builder, clauses, context):
        captured_clauses.extend(clauses)
        return original_build(builder, clauses, context)

    monkeypatch.setattr(ProtocolRowBuilder, "build", capture_build)

    with TestClient(app) as client:
        response = client.post(f"/api/documents/{doc.id}/protocol")

    assert response.status_code == 201, response.text
    row = response.json()["rows"][0]
    assert row["point_label"] == "Приложение № 1"
    assert row["party_1_text"] == "Старое\nПродолжение"
    assert row["party_2_text"] == "Новое\nПродолжение"
    restored_paragraphs = captured_clauses[0].paragraphs
    assert [paragraph.rendered_number for paragraph in restored_paragraphs] == ["1.", "1.1."]
    assert all(paragraph.rendered_number != "Приложение № 1" for paragraph in restored_paragraphs)
    assert doc.validation_report["numbering_confidence_mean"] == pytest.approx(0.6)


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
    party_1_text/party_2_text MUST NOT change -- they are bound to the
    original-vs-accepted data, not to which party is currently drafting.
    """
    doc, p1, p2 = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        before = proto["rows"][0]
        assert before["party_1_text"] == "Старый"
        assert before["party_2_text"] == "Новый"
        assert before["agreed_text"] == "Редакция Арендатора"
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        after = r2.json()["rows"][0]
        assert after["party_1_text"] == "Старый"
        assert after["party_2_text"] == "Новый"
        assert after["agreed_text"] == "Редакция Арендодателя"


def test_swap_parties_preserves_user_edited_agreed_text(doc_with_changes):
    """Rows whose agreed_text was manually edited keep their custom value
    after a swap (we recompute only rows where user_edited == False).
    """
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        client.patch(
            f"/api/protocols/{proto['id']}/rows/{row_id}",
            json={"agreed_text": "Согласовано вручную"},
        )
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        assert r2.json()["rows"][0]["agreed_text"] == "Согласовано вручную"


def test_swap_parties_skips_user_edited_row_even_when_agreed_text_is_auto(doc_with_changes):
    """A row marked user_edited=True (e.g. user changed point_label or
    party_1_text but left agreed_text at the auto-generated value) keeps
    its agreed_text after a swap -- we trust the explicit user_edited flag,
    not a string comparison against the old auto-label.
    """
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        client.patch(f"/api/protocols/{proto['id']}/rows/{row_id}", json={"point_label": "1.1."})
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        after = r2.json()["rows"][0]
        assert after["user_edited"] is True
        assert after["agreed_text"] == "Редакция Арендатора"


def test_swap_parties_recomputes_when_user_edited_false(doc_with_changes):
    """Sanity check the inverse: a row with user_edited=False has its
    agreed_text recomputed to the new drafting role's auto-label.
    """
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        assert proto["rows"][0]["user_edited"] is False
        r2 = client.post(f"/api/protocols/{proto['id']}/swap-parties")
        assert r2.status_code == 200, r2.text
        assert r2.json()["rows"][0]["agreed_text"] == "Редакция Арендодателя"


def test_get_protocol_rows_returns_existing_without_rebuild(doc_with_changes):
    """GET /protocols/{pid}/rows returns the persisted rows (including user
    edits) without triggering a rebuild that would wipe them.
    """
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r = client.post(f"/api/documents/{doc.id}/protocol")
        proto = r.json()
        row_id = proto["rows"][0]["id"]
        client.patch(f"/api/protocols/{proto['id']}/rows/{row_id}", json={"agreed_text": "Согласовано"})
        r2 = client.get(f"/api/protocols/{proto['id']}/rows")
        assert r2.status_code == 200
        body = r2.json()
        assert len(body["rows"]) == 1
        assert body["rows"][0]["agreed_text"] == "Согласовано"
        assert body["rows"][0]["user_edited"] is True


def test_list_protocols_for_document(doc_with_changes):
    """GET /protocols?document_id=... returns the protocol(s) for a document
    so the frontend can decide whether to load or build.
    """
    doc, _, _ = doc_with_changes
    with TestClient(app) as client:
        r0 = client.get("/api/protocols", params={"document_id": str(doc.id)})
        assert r0.status_code == 200
        assert r0.json() == []
        client.post(f"/api/documents/{doc.id}/protocol")
        r1 = client.get("/api/protocols", params={"document_id": str(doc.id)})
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
