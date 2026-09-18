from pathlib import Path


def test_expected_dag_files_are_present() -> None:
    dags = Path(__file__).parents[1] / "airflow" / "dags"
    dag_files = {path.name for path in dags.glob("*.py") if path.name not in {"__init__.py", "mct_airflow_utils.py"}}

    assert dag_files == {
        "daily_static_pipeline.py",
        "realtime_collection.py",
        "realtime_incremental_refresh.py",
    }
