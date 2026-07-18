"""Cloud-ready storage abstraction for local files and optional S3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mobility_control_tower.settings import AppSettings, get_settings


class StorageBackend(Protocol):
    def write_bytes(self, key: str, content: bytes) -> str: ...

    def read_bytes(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def list_keys(self, prefix: str = "") -> list[str]: ...


@dataclass(frozen=True)
class LocalStorage:
    root: Path

    def _path(self, key: str) -> Path:
        clean = key.lstrip("/")
        return self.root / clean

    def write_bytes(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        files = [path for path in base.rglob("*") if path.is_file()]
        return sorted(str(path.relative_to(self.root)) for path in files)


@dataclass(frozen=True)
class S3Storage:
    bucket: str
    prefix: str = ""
    region_name: str | None = None

    def _client(self):
        import boto3

        return boto3.client("s3", region_name=self.region_name)

    def _key(self, key: str) -> str:
        parts = [self.prefix.strip("/"), key.lstrip("/")]
        return "/".join(part for part in parts if part)

    def write_bytes(self, key: str, content: bytes) -> str:
        s3_key = self._key(key)
        self._client().put_object(Bucket=self.bucket, Key=s3_key, Body=content)
        return f"s3://{self.bucket}/{s3_key}"

    def read_bytes(self, key: str) -> bytes:
        response = self._client().get_object(Bucket=self.bucket, Key=self._key(key))
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self._client().head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except Exception:
            return False

    def list_keys(self, prefix: str = "") -> list[str]:
        s3_prefix = self._key(prefix)
        response = self._client().list_objects_v2(Bucket=self.bucket, Prefix=s3_prefix)
        return sorted(item["Key"] for item in response.get("Contents", []))


def get_storage_backend(settings: AppSettings | None = None) -> StorageBackend:
    resolved = settings or get_settings()
    backend = resolved.storage_backend.lower()
    if backend == "local":
        return LocalStorage(Path(resolved.storage_root))
    if backend == "s3":
        if not resolved.s3_bucket:
            raise ValueError("MCT_S3_BUCKET is required when MCT_STORAGE_BACKEND=s3")
        return S3Storage(resolved.s3_bucket, resolved.s3_prefix, resolved.aws_region)
    raise ValueError(f"Unsupported storage backend: {resolved.storage_backend}")

