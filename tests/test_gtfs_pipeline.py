import csv
import hashlib
import json
import zipfile
from pathlib import Path

from mobility_control_tower.quality.gtfs_quality import validate_silver_run
from mobility_control_tower.transformations.gtfs_bronze import build_bronze
from mobility_control_tower.transformations.gtfs_silver import build_silver, parse_gtfs_date, parse_gtfs_time


def fake_gtfs_files() -> dict[str, str]:
    return {
        "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nA1,Tisseo,https://example.test,Europe/Paris\n",
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,Capitole,43.6045,1.4440\nS2,Invalid,95,200\nS2,Duplicate,43.6,1.4\n",
        "routes.txt": "route_id,route_short_name,route_type\nR1,A,1\n",
        "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1\nUNKNOWN,WK,T2\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,24:10:00,25:30:00,S1,1\nUNKNOWN,invalid,08:00:00,UNKNOWN,2\n",
        "calendar.txt": "service_id,start_date,end_date\nWK,20260101,20260131\n",
    }


def make_raw_run(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    raw_run = tmp_path / "raw" / "tisseo" / "2026-01-02_030405"
    raw_run.mkdir(parents=True)
    files = fake_gtfs_files()
    archive_path = raw_run / "Tisseo_GTFS.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    metadata = {"sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()}
    (raw_run / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return raw_run, files


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def check(report: dict, name: str) -> dict:
    return next(item for item in report["checks"] if item["check_name"] == name)


def test_bronze_extracts_original_content_and_manifest(tmp_path: Path) -> None:
    raw_run, files = make_raw_run(tmp_path)
    bronze_run = build_bronze(raw_run, tmp_path / "bronze")
    manifest = json.loads((bronze_run / "bronze_manifest.json").read_text(encoding="utf-8"))

    assert (bronze_run / "stops.txt").read_text(encoding="utf-8") == files["stops.txt"]
    assert manifest["source_zip_sha256"]
    assert manifest["extracted_files"]["stops.txt"]["row_count"] == 3
    assert manifest["extracted_files"]["routes.txt"]["columns"] == ["route_id", "route_short_name", "route_type"]
    assert "calendar_dates.txt" in manifest["missing_important_files"]


def test_silver_tables_and_after_midnight_times(tmp_path: Path) -> None:
    raw_run, _ = make_raw_run(tmp_path)
    bronze_run = build_bronze(raw_run, tmp_path / "bronze")
    silver_run = build_silver(bronze_run, tmp_path / "silver")
    stop_times = read_csv(silver_run / "stop_times.csv")
    manifest = json.loads((silver_run / "silver_manifest.json").read_text(encoding="utf-8"))

    assert parse_gtfs_time("08:15:00") == 29_700
    assert parse_gtfs_time("24:10:00") == 87_000
    assert parse_gtfs_time("25:30:00") == 91_800
    assert parse_gtfs_time("invalid") is None
    assert parse_gtfs_time("") is None
    assert parse_gtfs_date("20260131") == "2026-01-31"
    assert parse_gtfs_date("20260231") is None
    assert stop_times[0]["arrival_time"] == "24:10:00"
    assert stop_times[0]["arrival_time_seconds"] == "87000"
    assert manifest["tables_created"]["trips"]["row_count"] == 2
    assert read_csv(silver_run / "calendar.csv")[0]["start_date_iso"] == "2026-01-01"


def test_quality_detects_duplicates_coordinates_and_unknown_references(tmp_path: Path) -> None:
    raw_run, _ = make_raw_run(tmp_path)
    bronze_run = build_bronze(raw_run, tmp_path / "bronze")
    silver_run = build_silver(bronze_run, tmp_path / "silver")
    json_path, markdown_path = validate_silver_run(silver_run, tmp_path / "reports")
    report = json.loads(json_path.read_text(encoding="utf-8"))

    assert check(report, "duplicate_stop_id")["problem_count"] == 1
    assert check(report, "invalid_stop_lat")["problem_count"] == 1
    assert check(report, "invalid_stop_lon")["problem_count"] == 1
    assert check(report, "stop_times_unknown_trip_id")["problem_count"] == 1
    assert check(report, "stop_times_unknown_stop_id")["problem_count"] == 1
    assert check(report, "trips_unknown_route_id")["problem_count"] == 1
    assert check(report, "invalid_arrival_time_format")["problem_count"] == 1
    assert report["overall_status"] == "FAIL"
    assert markdown_path.is_file()


def test_quality_detects_missing_required_column(tmp_path: Path) -> None:
    silver_run = tmp_path / "silver" / "tisseo" / "run-1"
    silver_run.mkdir(parents=True)
    (silver_run / "stops.csv").write_text("stop_id,stop_name,stop_lat\nS1,Capitole,43.6\n", encoding="utf-8")
    json_path, _ = validate_silver_run(silver_run, tmp_path / "reports")
    report = json.loads(json_path.read_text(encoding="utf-8"))

    required = check(report, "stops_required_columns")
    assert required["status"] == "FAIL"
    assert required["problem_count"] == 1
    assert "stop_lon" in required["explanation"]
