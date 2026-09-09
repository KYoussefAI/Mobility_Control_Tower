# Contributing

Mobility Control Tower is a local-first academic MVP and portfolio project that
uses production-inspired engineering practices. Keep that scope explicit and
avoid claims of agency deployment, universal GTFS support, or distributed scale.

## Development workflow

New changes use a focused branch, pull request, and CI review before merging to
`main`:

1. Branch from an up-to-date `main`.
2. Implement one coherent change with its tests and documentation.
3. Run the checks supported by the repository.
4. Open a pull request and let CI complete.
5. Merge only after required checks pass.

Keep pull requests focused and resolve all required CI failures before merging.

## Supported setup

```bash
python -m pip install -e ".[dev,quality,analytics]"
```

## Checks

```bash
ruff check .
black --check .
isort --check-only .
mypy src
coverage run -m pytest
coverage report --fail-under=80
dbt deps --project-dir dbt --profiles-dir dbt
dbt parse --project-dir dbt --profiles-dir dbt --no-partial-parse
```

Python owns ingestion and the Raw, Bronze, and Silver layers. dbt owns analytical
Gold.
