from pathlib import Path

from mobility_control_tower import cli


def test_cli_exposes_realtime_fetch_arguments() -> None:
    args = cli.build_parser().parse_args(["fetch-gtfs-rt", "--source", "test", "--feed-type", "trip_updates", "--url", "https://example.test/trips.pb"])
    assert args.command == "fetch-gtfs-rt"
    assert args.source == "test"
    assert args.feed_type == "trip_updates"


def test_cli_fetch_calls_acquisition_layer(monkeypatch, tmp_path: Path, capsys) -> None:
    expected = tmp_path / "raw" / "test" / "trip_updates" / "run"
    monkeypatch.setattr(cli, "load_source", lambda *args: {"name": "Test"})
    monkeypatch.setattr(cli, "fetch_realtime_snapshot", lambda *args, **kwargs: expected)
    monkeypatch.setattr(
        "sys.argv",
        [
            "mobility-control-tower",
            "fetch-gtfs-rt",
            "--source",
            "test",
            "--feed-type",
            "trip_updates",
            "--url",
            "https://example.test/trips.pb",
            "--raw-root",
            str(tmp_path / "raw"),
        ],
    )
    assert cli.main() == 0
    assert str(expected) in capsys.readouterr().out
