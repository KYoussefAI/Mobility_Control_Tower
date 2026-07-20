from __future__ import annotations

import importlib
import subprocess
import sys
import types
from pathlib import Path

AIRFLOW_DAGS = Path(__file__).resolve().parents[1] / "airflow" / "dags"


def install_fake_airflow(monkeypatch, variables: dict[str, str] | None = None):
    variables = variables or {}
    current = {"dag": None}

    class FakeVariable:
        requested: list[str] = []

        @classmethod
        def get(cls, name, default_var=None):
            cls.requested.append(name)
            return variables.get(name, default_var)

    class FakeDAG:
        def __init__(self, dag_id, default_args=None, schedule_interval=None, **kwargs):
            self.dag_id = dag_id
            self.default_args = default_args or {}
            self.schedule_interval = schedule_interval
            self.kwargs = kwargs
            self.task_dict = {}

        def __enter__(self):
            current["dag"] = self
            return self

        def __exit__(self, exc_type, exc, tb):
            current["dag"] = None

    class FakePythonOperator:
        def __init__(self, task_id, python_callable=None, **kwargs):
            self.task_id = task_id
            self.python_callable = python_callable
            self.upstream_task_ids = set()
            self.downstream_task_ids = set()
            self.dag = kwargs.get("dag") or current["dag"]
            if self.dag is not None:
                self.retries = self.dag.default_args.get("retries")
                self.retry_delay = self.dag.default_args.get("retry_delay")
                self.execution_timeout = self.dag.default_args.get("execution_timeout")
                self.dag.task_dict[task_id] = self

        def __rshift__(self, other):
            self.downstream_task_ids.add(other.task_id)
            other.upstream_task_ids.add(self.task_id)
            return other

    airflow = types.ModuleType("airflow")
    airflow.DAG = FakeDAG
    operators = types.ModuleType("airflow.operators")
    python = types.ModuleType("airflow.operators.python")
    python.PythonOperator = FakePythonOperator
    exceptions = types.ModuleType("airflow.exceptions")

    class FakeAirflowSkipException(Exception):
        pass

    exceptions.AirflowSkipException = FakeAirflowSkipException
    models = types.ModuleType("airflow.models")
    models.Variable = FakeVariable
    monkeypatch.setitem(sys.modules, "airflow", airflow)
    monkeypatch.setitem(sys.modules, "airflow.operators", operators)
    monkeypatch.setitem(sys.modules, "airflow.operators.python", python)
    monkeypatch.setitem(sys.modules, "airflow.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "airflow.models", models)
    monkeypatch.syspath_prepend(str(AIRFLOW_DAGS))
    return FakeVariable


def fresh_import(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_daily_static_dag_loads_with_expected_dependencies_and_retries(monkeypatch) -> None:
    install_fake_airflow(monkeypatch)
    module = fresh_import("daily_static_pipeline")
    dag = module.dag

    assert dag.dag_id == "daily_static_pipeline"
    assert dag.schedule_interval == "@daily"
    assert list(dag.task_dict) == [
        "ingest_gtfs",
        "profile_gtfs",
        "build_bronze",
        "build_silver",
        "validate_gtfs",
        "run_dbt_models",
        "validate_with_quality_contracts",
        "generate_static_charts",
        "generate_demo_report",
        "build_serving_db",
    ]
    assert dag.task_dict["ingest_gtfs"].downstream_task_ids == {"profile_gtfs"}
    assert dag.task_dict["profile_gtfs"].downstream_task_ids == {"build_bronze"}
    assert dag.task_dict["validate_gtfs"].downstream_task_ids == {"run_dbt_models"}
    assert dag.task_dict["run_dbt_models"].downstream_task_ids == {"validate_with_quality_contracts"}
    assert dag.task_dict["validate_with_quality_contracts"].downstream_task_ids == {"generate_static_charts"}
    assert dag.task_dict["generate_demo_report"].downstream_task_ids == {"build_serving_db"}
    assert all(task.retries == 3 for task in dag.task_dict.values())


def test_realtime_dag_loads_with_expected_dependencies_and_schedule(monkeypatch) -> None:
    install_fake_airflow(monkeypatch)
    module = fresh_import("realtime_collection")
    dag = module.dag

    assert dag.dag_id == "realtime_snapshot_collection"
    assert dag.schedule_interval == "* * * * *"
    assert dag.kwargs["max_active_runs"] == 1
    assert list(dag.task_dict) == ["collect_gtfs_rt"]
    assert dag.task_dict["collect_gtfs_rt"].downstream_task_ids == set()


def test_incremental_refresh_dag_loads_with_expected_dependencies(monkeypatch) -> None:
    install_fake_airflow(monkeypatch)
    module = fresh_import("realtime_incremental_refresh")
    dag = module.dag

    assert dag.dag_id == "realtime_incremental_refresh"
    assert dag.schedule_interval == "*/10 * * * *"
    assert dag.kwargs["max_active_runs"] == 1
    assert dag.task_dict["discover_new_snapshots"].downstream_task_ids == {"run_dbt_history"}
    assert dag.task_dict["run_dbt_history"].downstream_task_ids == {"validate_recent_quality"}
    assert dag.task_dict["validate_recent_quality"].downstream_task_ids == {"publish_serving_refresh"}
    assert dag.task_dict["publish_serving_refresh"].downstream_task_ids == {"evaluate_reliability_incidents"}
    assert dag.task_dict["evaluate_reliability_incidents"].downstream_task_ids == {"advance_refresh_watermark"}


def test_airflow_variables_are_used_for_pipeline_context(monkeypatch, tmp_path: Path) -> None:
    variable = install_fake_airflow(
        monkeypatch,
        {
            "mct_gtfs_source": "demo",
            "mct_realtime_feed_type": "trip_updates",
            "mct_history_root": str(tmp_path / "history"),
            "mct_pipeline_runs_root": str(tmp_path / "runs"),
            "mct_polling_interval": "17",
        },
    )
    utils = fresh_import("mct_airflow_utils")
    context = utils.pipeline_context()

    assert context["source"] == "demo"
    assert context["polling_interval"] == "17"
    assert context["history_run"] == str(tmp_path / "history" / "demo" / "trip_updates")
    assert "mct_gtfs_source" in variable.requested
    assert "mct_serving_root" in variable.requested


def test_cli_task_invokes_existing_cli_and_writes_metadata(monkeypatch, tmp_path: Path) -> None:
    install_fake_airflow(monkeypatch, {"mct_pipeline_runs_root": str(tmp_path / "pipeline_runs")})
    utils = fresh_import("mct_airflow_utils")
    calls: list[list[str]] = []

    class Completed:
        stdout = "Gold KPI tables written to: data/gold/tisseo/run-1\n"
        stderr = ""

    def fake_run(command, cwd, text, capture_output, check):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    class Dag:
        dag_id = "unit_dag"

    class Task:
        task_id = "build_gold"

    output = utils.run_cli_task(
        task_id="build_gold",
        command_args=["build-gold", "--silver-run", "data/silver/tisseo/run-1"],
        output_label="Gold KPI tables written to",
        context={"dag": Dag(), "task": Task(), "run_id": "manual__unit"},
    )
    metadata = tmp_path / "pipeline_runs" / "unit_dag" / "manual__unit" / "build_gold.json"

    assert output == "data/gold/tisseo/run-1"
    assert calls[0][-3:] == ["build-gold", "--silver-run", "data/silver/tisseo/run-1"]
    assert metadata.is_file()
    assert '"status": "success"' in metadata.read_text(encoding="utf-8")


def test_cli_task_writes_failed_metadata(monkeypatch, tmp_path: Path) -> None:
    install_fake_airflow(monkeypatch, {"mct_pipeline_runs_root": str(tmp_path / "pipeline_runs")})
    utils = fresh_import("mct_airflow_utils")

    def fake_run(command, cwd, text, capture_output, check):
        raise subprocess.CalledProcessError(1, command, output="bad stdout", stderr="bad stderr")

    monkeypatch.setattr(subprocess, "run", fake_run)

    class Dag:
        dag_id = "unit_dag"

    class Task:
        task_id = "fail_task"

    try:
        utils.run_cli_task(
            task_id="fail_task",
            command_args=["validate-gtfs", "--silver-run", "missing"],
            context={"dag": Dag(), "task": Task(), "run_id": "manual__failed"},
        )
    except subprocess.CalledProcessError:
        pass

    metadata = tmp_path / "pipeline_runs" / "unit_dag" / "manual__failed" / "fail_task.json"
    assert metadata.is_file()
    assert '"status": "failed"' in metadata.read_text(encoding="utf-8")
