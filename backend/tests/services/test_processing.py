import uuid

from app.models.clause import Clause as ClauseModel
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.party import Party
from app.services.processing import process_document
from tests.fixtures.builders import build_docx_with_table_cell_replacement


class _FakeStorage:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def get(self, key: str) -> bytes:
        assert key == "table-key"
        return self.data


class _FakeSession:
    def __init__(self, document: Document) -> None:
        self.document = document
        self.clauses: list[ClauseModel] = []
        self.parties: list[Party] = []

    def get(self, model, object_id):
        if model is Document and object_id == self.document.id:
            return self.document
        return None

    def add(self, obj) -> None:
        if isinstance(obj, ClauseModel):
            self.clauses.append(obj)
        elif isinstance(obj, Party):
            self.parties.append(obj)

    def commit(self) -> None:
        pass

    def close(self) -> None:
        pass


def test_process_document_persists_versioned_table_cells(monkeypatch):
    document = Document(
        id=uuid.uuid4(),
        original_filename="table.docx",
        storage_key="table-key",
        contract_name="Договор",
        status=DocumentStatus.UPLOADED,
    )
    db = _FakeSession(document)

    monkeypatch.setattr("app.services.processing.SessionLocal", lambda: db)
    monkeypatch.setattr(
        "app.services.processing.FileStorage",
        lambda: _FakeStorage(build_docx_with_table_cell_replacement()),
    )

    process_document(str(document.id))

    table_clauses = [clause for clause in db.clauses if clause.tables_json]
    assert table_clauses
    table = table_clauses[0].tables_json[0]
    assert table["rows"][1][1] == {
        "original_text": "1 200",
        "accepted_text": "1 100",
        "revisions": [
            {"type": "DEL", "text": "1 200", "author": "Юрист контрагента"},
            {"type": "INS", "text": "1 100", "author": "Юрист контрагента"},
        ],
    }
    assert table["rows"][0][0] == {
        "original_text": "Период",
        "accepted_text": "Период",
        "revisions": [],
    }
    assert table["rows"][0][2] == {
        "original_text": "Итого",
        "accepted_text": "Итого",
        "revisions": [],
    }
