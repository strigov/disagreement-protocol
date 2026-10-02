"""Small additive migrations for the local SQLite database. Never rebuild user tables."""
from sqlalchemy import inspect

from app.db.base import Base


def upgrade_schema(engine) -> None:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    additions = {
        "protocols": {"form_json": "JSON"},
        "protocol_rows": {
            "source_clause_keys": "JSON",
            "agreed_text_edited": "BOOLEAN",
        },
        "clauses": {"paragraphs_json": "JSON"},
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {c["name"] for c in inspect(connection).get_columns(table)}
            for column, sql_type in columns.items():
                if column not in existing:
                    # Names and types are fixed application constants, never user input.
                    connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
