# Engineering Audit

## Architecture

Mobility Control Tower is a local-first batch and scheduled-polling platform. Python owns GTFS/GTFS-Realtime acquisition, immutable Raw captures, Bronze extraction, Silver normalization, committed realtime Parquet snapshots, operational state, and interfaces. dbt reads Silver and historical Parquet and is the production authority for Gold marts. DuckDB publishes immutable run-scoped analytical artifacts behind a replace-on-success `current.json` pointer. SQLite or PostgreSQL stores mutable incident state. Airflow invokes application CLI commands; FastAPI and Streamlit consume serving views and incident repositories. Prometheus/Grafana observe bounded operational metrics.

## Data flow

Static: source ZIP -> checksummed Raw run -> Bronze extracted files/manifest -> typed Silver CSV -> dbt staging/intermediate/marts -> exported Gold CSV/Parquet and dbt manifest -> mandatory quality contracts -> validated DuckDB candidate -> run directory -> current pointer -> API/dashboard/incident evaluation/metrics.

Realtime: HTTP polling -> checksummed protobuf Raw snapshot -> parsed tables -> content-addressed committed Parquet snapshot partitions -> dbt historical/reliability marts -> history quality gate -> validated DuckDB publication -> incident evaluation -> watermark advancement. This is snapshot polling, not event streaming. Source timestamps, collection/ingestion timestamps, and publication timestamps remain distinct where the source provides them.

## Sources of truth

- Reliability, route/headway, delay, cancellation, coverage, and Gold business metrics: dbt marts.
- Snapshot-level diagnostic reports and legacy Python Gold builders: diagnostics only, not production Gold.
- Quality results: MCT quality-contract JSON output; a failed status is publication-blocking.
- Incidents and audit history: incident repository (SQLite locally, PostgreSQL in the composed runtime), evaluated from serving outputs.
- Incremental progress: per-source/feed/workflow watermark JSON.
- Current analytical artifact: `data/serving/<source>/current.json`, resolved to an immutable serving run.

## P0/P1 problems found

- **P1 — verification dependency gap:** the supported dev extra omitted the HTTP client required by FastAPI/Starlette's test client, so a clean install could not collect API tests.
- **P1 — dbt executable discovery:** dbt was installed but the wrapper only searched `PATH`; isolated Python installations failed real dbt builds despite a valid installation.
- **P1 — broken CI parity inputs:** direct dbt CI commands supplied relative fixture paths, which DuckDB resolved relative to the database directory rather than the repository.
- **P1 — unsafe publication state:** an explicitly failed quality status could still be published as current.
- **P1 — incorrect watermark provenance:** the realtime Airflow task stored `runs` instead of the actual serving run ID.
- **P1 — local storage boundary/portability:** keys permitted parent traversal and returned Windows separators, breaking the backend's portable key contract.
- **P2 — documentation sprawl:** several overlapping portfolio/demo documents remain; reconciliation should be incremental rather than a risky bulk deletion.

## Major fixes

- Added the missing test-client dependency and made dbt discovery fall back to the active interpreter's scripts directory.
- Resolved CI fixture paths before direct dbt full-refresh/incremental/idempotency builds.
- Rejected traversal/non-portable local storage keys and normalized returned keys to POSIX form.
- Blocked current-pointer publication for explicit failed/invalid/blocked quality states; Airflow now marks publication `passed` only downstream of successful validation.
- Corrected the serving run ID written to realtime watermarks and extended regression tests.

## Architecture decisions

- dbt remains the sole production Gold authority; no Python fallback was introduced.
- Publication remains run-scoped candidate build -> structural validation -> manifest -> directory rename -> replace-on-success pointer.
- Watermarks remain last and advance only after dbt, quality, publication, and incident evaluation succeed.
- Unknown quality status is retained for explicit diagnostic/manual compatibility; failed status can never replace current.

## Tests actually run

- `ruff check .`: pass.
- `black --check .`: pass.
- `isort --check-only .`: pass.
- `mypy src`: pass (56 files).
- Initial `pytest -q`: 4 failures (three dbt discovery failures and one path portability failure), plus the clean-install test-client collection gap.
- Targeted dbt/storage/serving/Airflow suite after fixes: pass (30 tests, including real dbt build).
- `coverage run -m pytest -q`: pass (99 passed, 1 environment-gated PostgreSQL test skipped); `coverage report --fail-under=80`: pass at 80% branch coverage.
- `dbt deps` and `dbt parse --no-partial-parse`: pass.
- Deterministic `dbt build --full-refresh`: pass, 283/283 models/tests/unit tests.
- Incremental/full-refresh comparison and second incremental idempotency comparison: pass.
- Grafana metric-expression validation: pass (18 expressions).
- Docker/Compose/runtime closure: pass on Docker Desktop 4.87.0 / Engine 29.7.2 / Compose 5.4.0; detailed evidence is recorded in the final runtime closure below.

## Final status

**PASS.** The non-Docker gates and the final Docker/Compose, PostgreSQL, Airflow, serving-safety, API/dashboard, observability, failure/recovery, and release-evidence gates pass. No known P0/P1 runtime blocker remains. The production overlay was rendered and contract-verified, not deployed to a public production environment.

## Remaining technical debt

- The incident module still combines domain, evaluation, repository, and service concerns. Its SQLite/PostgreSQL behavior is now runtime-proven; extraction remains a deliberate follow-up refactor, not a release blocker.
- The platform remains a local-first polling system. It does not claim event streaming, multi-node/high-availability operation, cloud deployment, or transit-agency production usage.
- Docker Desktop was constrained to approximately 2 GB RAM and the Windows C: drive reached zero free bytes during a final image import. Reproducible BuildKit, Playwright, package-manager, and temporary caches were cleared; no project data or Docker volumes were removed. The final image was rebuilt and validated after recovery.

## Recommended Phase 2 work

1. Split incident persistence adapters from evaluation/application services without changing behavior.
2. Consolidate stale portfolio/demo documentation into README, runbook, this audit, and the KPI dictionary.
3. If production deployment becomes a real requirement, add environment-specific capacity, HA, secret-management, and recovery objectives rather than implying them from the local runtime proof.

## Non-Docker closure pass

### API route topology

Before closure, the same router was mounted at `/` and `/v1` while incident decorators already contained `/v1`. OpenAPI therefore exposed accidental `/v1/v1/incidents...` paths, duplicate canonical/read surfaces, and two separate acknowledge/resolve implementations. No project consumer used the legacy mutation implementations.

After closure, route definitions are version-neutral and mounted once at canonical `/v1`. Unversioned GET routes remain deprecated, schema-hidden compatibility reads. Unversioned mutations are absent (404), incident mutations have one implementation, and scoped authentication remains mandatory. The dashboard now consumes canonical `/v1` endpoints and passes its operator token to protected incident reads.

### Watermark failure-boundary evidence

Focused callable tests execute the required refresh stages in dependency order and inject failures at dbt, mandatory quality, serving publication, and incident evaluation. Each failure proves the watermark callable is never invoked. The success test invokes the real watermark callable and proves it records both `snapshot-2` and published run `serving-42` with `success` status.

### Incremental model grain and unique-key audit

All incremental models use `delete+insert`, contain no `is_incremental()` source filter, and recompute from the complete selected committed history. Late inputs therefore replace the affected logical grain; repeated equivalent inputs replace identical keys rather than append duplicates.

| Model | Business grain | `unique_key` | Why unique / late and repeated behavior | Result |
|---|---|---|---|---|
| `daily_summary` | collection date | `collection_date` | One grouped row per date; a late snapshot replaces that day's aggregate | Correct |
| `delay_evolution_by_hour` | collection date + hour | `[collection_date, collection_hour]` | Matches both grouping columns; late observations replace the hour | Correct |
| `feed_freshness_trend` | collection date + hour | `[collection_date, collection_hour]` | Matches both grouping columns; repeated snapshots recalculate the bucket | Correct |
| `trip_match_trend` | collection date + hour | `[collection_date, collection_hour]` | Matches both grouping columns; late matches replace the bucket | Correct |
| `route_delay_history` | route within the run's single source | `route_id` | Model selects one source-scoped history root and groups only by route; full-history recomputation replaces the route aggregate | Correct and source-scope justified |
| `stop_delay_history` | stop within the run's single source | `stop_id` | Model selects one source-scoped history root and groups only by stop; full-history recomputation replaces the stop aggregate | Correct and source-scope justified |
| `fct_realtime_delay_observations` | source + snapshot + trip + stop/sequence + selected event | `delay_observation_key` | Deterministic hash includes all identity components and event convention; repeated snapshots replace the observation | Correct |
| `fct_explicit_trip_cancellations` | source + service date + trip + explicit cancellation evidence type | `cancellation_evidence_key` | GTFS trip ID is feed-unique; route is an attribute, not an additional grain; later sightings update first/last evidence | Correct |
| `fct_observed_headways` | source + service date + route + direction + reference stop + leading/following trip + method | `headway_key` | Deterministic hash covers the documented pair/event grain; late observations recalculate pair ordering and replace keys | Correct |
| `fct_headway_reliability_events` | one classification for an observed headway | `evidence_key` | Deterministic derivative of `headway_key` plus event identity; threshold changes or late data replace current evidence | Correct |

No key defect was found; dbt SQL was unchanged. Existing schema uniqueness tests and the previously passed full-refresh/incremental/idempotency comparisons support these conclusions.

### Documentation and dead configuration

- Canonical `/v1` paths, compatibility policy, authentication, dashboard, configured observability, polling semantics, and runtime boundaries are now stated consistently in the API docs/report, project summary, demo guide, README, and dashboard client.
- The demo guide now uses dbt Gold and a mandatory quality gate instead of the legacy Python Gold builder.
- The lone `great_expectations/great_expectations.yml` file had no executable reference or dependency; it was removed. `quality_contracts/` remains the sole authoritative MCT quality system. The `run-ge-validation` CLI name remains only as an explicitly deprecated compatibility alias.

### Incident decomposition decision

No incident-module extraction was needed for API cleanup; duplicate behavior lived in route functions and was removed there. The current module keeps domain transitions, rule evaluation, repository protocols, SQLite/PostgreSQL adapters, and application orchestration together to avoid broad structural churn after the runtime contract was closed.

### Closure verification

Non-Docker closure status: **PASS**.

- `python -m pytest tests/test_api.py tests/test_incident_engine.py tests/test_phase3_operator_intelligence.py tests/test_airflow_dags.py tests/test_final_demo.py tests/test_cli_dashboard_coverage.py -q`: 46 passed.
- `python -m pytest tests/test_historical_realtime.py::test_history_api_endpoints_and_dashboard_client_names -q`: 1 passed.
- `ruff check .`: pass.
- `black --check .`: pass, 107 files unchanged (one new test file was formatted before the passing check).
- `isort --check-only .`: pass, configured exclusions reported as skipped.
- `mypy src`: pass, 56 source files.
- `dbt parse --project-dir dbt --profiles-dir dbt --no-partial-parse`: pass. No dbt model changed, so the previously passed full-refresh/parity/idempotency proof was not repeated.
- `coverage run -m pytest -q`: 105 passed, 1 PostgreSQL environment-gated skip.
- `coverage report --fail-under=80`: pass at 80% branch coverage.

The Docker-dependent items listed above were subsequently completed in the final runtime closure below.

## Runtime verification status

Static configuration and non-Docker checks are reproducible from this repository.
A fresh Docker image build, running-service verification, browser capture, and
PostgreSQL recovery exercise still require a reachable Docker daemon.

The repository provides fail-closed scripts and a `release-proof` CI job for
those checks. Runtime success must be reported only from a completed execution;
historical image digests, screenshots, or service-health claims are not treated
as current evidence.

Use `docs/final_demo_guide.md` for the exact local commands. Generated databases,
logs, screenshots, and evidence bundles remain untracked.
