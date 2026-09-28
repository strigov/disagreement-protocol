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

    def one_or_none(self):
        rows = self.all()
        if len(rows) > 1:
            raise AssertionError("Expected at most one row")
        return rows[0] if rows else None


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
        self.committed = False

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

    def flush(self) -> None:
        for collection in (self.parties, self.clauses, self.protocols, self.rows):
            for obj in collection:
                if obj.id is None:
                    obj.id = uuid.uuid4()

    def commit(self) -> None:
        self.committed = True
        self.flush()

    def close(self) -> None:
        pass

    def get(self, model, obj_id):
        if model is Document and obj_id == self.doc.id:
            return self.doc
        if model is Protocol:
            return next((protocol for protocol in self.protocols if protocol.id == obj_id), None)
        if model is ProtocolRow:
            return next((row for row in self.rows if row.id == obj_id), None)
        return None

    def execute(self, statement):
        return FakeScalarResult(self.doc)

    def query(self, model):
        return FakeQuery(self, model)


@pytest.fixture
def ready_doc() -> Iterator[tuple[Document, FakeDb]]:
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
        yield doc, db
    finally:
        app.dependency_overrides.clear()


def test_export_endpoint_returns_docx_bytes(ready_doc):
    doc, db = ready_doc
    with TestClient(app, base_url="http://localhost") as client:
        client.post(f"/api/documents/{doc.id}/protocol")
        response = client.post(f"/api/documents/{doc.id}/protocol/export", json={"filename": "Протокол"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    content_disposition = response.headers["content-disposition"]
    assert "filename=" in content_disposition
    assert "filename*=UTF-8''" in content_disposition
    assert response.content[:2] == b"PK"
    assert doc.status == DocumentStatus.EXPORTED
    assert db.committed is True
