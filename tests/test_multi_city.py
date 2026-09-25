from pathlib import Path

import yaml

from mobility_control_tower.settings import AppSettings
from mobility_control_tower.storage import LocalStorage, get_storage_backend


def test_source_catalogue_contains_two_distinct_cities() -> None:
    sources = yaml.safe_load(Path("config/sources.yml").read_text(encoding="utf-8"))["sources"]

    assert {source["city"] for source in sources.values()} == {"Toulouse", "Rennes"}
    assert all(source["static_gtfs"]["url"].startswith("https://") for source in sources.values())


def test_local_storage_round_trip_remains_the_default(tmp_path: Path) -> None:
    settings = AppSettings(storage_root=str(tmp_path))

    backend = get_storage_backend(settings)
    location = backend.write_bytes("rennes/realtime/sample.pb", b"payload")

    assert isinstance(backend, LocalStorage)
    assert Path(location).read_bytes() == b"payload"
    assert backend.list_keys("rennes") == ["rennes/realtime/sample.pb"]
