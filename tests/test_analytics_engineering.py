from pathlib import Path


def test_static_dbt_project_has_expected_model_layers() -> None:
    project = Path(__file__).parents[1] / "dbt"

    assert (project / "dbt_project.yml").is_file()
    assert (project / "models" / "staging").is_dir()
    assert (project / "models" / "intermediate").is_dir()
    assert (project / "models" / "marts").is_dir()


def test_static_gold_models_are_present() -> None:
    gold = Path(__file__).parents[1] / "dbt" / "models" / "marts"
    model_names = {path.stem for path in gold.glob("*.sql")}

    assert {
        "network_daily_summary",
        "route_daily_trips",
        "route_period_summary",
    }.issubset(model_names)
