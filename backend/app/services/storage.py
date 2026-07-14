from __future__ import annotations

from pathlib import Path

from app.config import get_settings


class FileStorage:
    """Stores uploaded documents as plain files under settings.storage_dir."""

    def __init__(self) -> None:
        self._root = Path(get_settings().storage_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError(f"Storage key escapes storage dir: {key}")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()
