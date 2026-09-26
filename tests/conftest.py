from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def gtfs_zip_bytes() -> bytes:
    fixture_dir = Path(__file__).parent / "fixtures" / "static"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(fixture_dir.glob("*.txt")):
            archive.write(path, path.name)
    return buffer.getvalue()
