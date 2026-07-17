import json
import zipfile
from pathlib import Path

from mobility_control_tower.profiling.gtfs_profile import build_profile, profile_raw_run


def make_gtfs(path: Path, include_calendar: bool = True) -> None:
    contents = {
        "agency.txt": "agency_id,agency_name\n1,Tisseo\n",
        "stops.txt": "stop_id,stop_name\nS1,Capitole\nS2,Matabiau\n",
        "routes.txt": "route_id,route_short_name\nR1,A\n",
        "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1\nR1,WK,T2\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,S1,1\nT1,08:05:00,08:05:00,S2,2\n",
    }
    if include_calendar:
        contents["calendar.txt"] = "service_id,monday,start_date,end_date\nWK,1,20260101,20260131\n"
    with zipfile.ZipFile(path, "w") as archive:
        for filename, content in contents.items():
            archive.writestr(filename, content)


def test_profile_detects_files_counts_columns_and_dates(tmp_path: Path) -> None:
    gtfs_zip = tmp_path / "fake.zip"
    make_gtfs(gtfs_zip)
    profile = build_profile(gtfs_zip, "run-1")
    assert profile["important_files_present"]["routes.txt"] is True
    assert profile["files"]["stops.txt"]["row_count"] == 2
    assert profile["files"]["stops.txt"]["columns"] == ["stop_id", "stop_name"]
    assert profile["number_of_routes"] == 1
    assert profile["number_of_trips"] == 2
    assert profile["service_date_range"] == {"start_date": "20260101", "end_date": "20260131"}


def test_profile_handles_missing_files_and_writes_reports(tmp_path: Path) -> None:
    run_dir = tmp_path / "raw" / "tisseo" / "2026-01-02_030405"
    run_dir.mkdir(parents=True)
    make_gtfs(run_dir / "Tisseo_GTFS.zip", include_calendar=False)
    json_path, markdown_path = profile_raw_run(run_dir, tmp_path / "reports")
    profile = json.loads(json_path.read_text(encoding="utf-8"))
    assert set(profile["missing_important_files"]) == {"calendar.txt", "calendar_dates.txt"}
    assert profile["important_files_present"]["calendar_dates.txt"] is False
    assert profile["service_date_range"] == {"start_date": None, "end_date": None}
    assert markdown_path.is_file()
