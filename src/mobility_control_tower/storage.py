"""Local filesystem storage used by the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class LocalStorage:
    root: Path

    def _path(self, key: str) -> Path:
        if "\\" in key:
            raise ValueError("Storage keys must use forward slashes")
        clean = PurePosixPath(key)
        if clean.is_absolute() or not clean.parts or any(part in {"", ".", ".."} for part in clean.parts):
            raise ValueError(f"Invalid storage key: {key!r}")
        return self.root.joinpath(*clean.parts)

    def write_bytes(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path.as_posix()

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self.root if not prefix else self._path(prefix)
        if not base.exists():
            return []
        return sorted(path.relative_to(self.root).as_posix() for path in base.rglob("*") if path.is_file())


def get_storage_backend(root: Path = Path("data")) -> LocalStorage:
    return LocalStorage(root)
