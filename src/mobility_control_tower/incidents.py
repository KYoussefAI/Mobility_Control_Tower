"""Deterministic operational incident evaluation and persistence.

The incident evaluator consumes authoritative serving and platform manifests.
It does not recompute reliability KPIs that are owned by dbt marts.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import urlsplit, urlunsplit

import duckdb

from mobility_control_tower.config import load_sources
from mobility_control_tower.realtime.historical_storage import discover_committed_snapshots
from mobility_control_tower.serving.duckdb_loader import read_current_pointer, resolve_current_database

INCIDENT_SCHEMA_VERSION = 2
OPEN_STATUSES = {"OPEN", "ACKNOWLEDGED", "MONITORING"}
ACTIVE_STATUSES = OPEN_STATUSES | {"SUPPRESSED"}
SYSTEM_ACTOR = "incident-evaluator"
DEFAULT_INCIDENT_ROOT = Path("data/incidents")


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class CandidateState(str, Enum):
    UNHEALTHY = "UNHEALTHY"
    HEALTHY = "HEALTHY"
    NOT_ENOUGH_DATA = "NOT_ENOUGH_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class EventType(str, Enum):
    OPENED = "OPENED"
    OBSERVED_AGAIN = "OBSERVED_AGAIN"
    EVIDENCE_UPDATED = "EVIDENCE_UPDATED"
    SEVERITY_ESCALATED = "SEVERITY_ESCALATED"
    SEVERITY_DEESCALATED = "SEVERITY_DEESCALATED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    MONITORING_STARTED = "MONITORING_STARTED"
    AUTO_RESOLVED = "AUTO_RESOLVED"
    MANUALLY_RESOLVED = "MANUALLY_RESOLVED"
    SUPPRESSED = "SUPPRESSED"
    SUPPRESSION_EXPIRED = "SUPPRESSION_EXPIRED"
    REOPENED = "REOPENED"
    EVALUATION_SKIPPED = "EVALUATION_SKIPPED"


VALID_TRANSITIONS = {
    IncidentStatus.OPEN: {IncidentStatus.ACKNOWLEDGED, IncidentStatus.MONITORING, IncidentStatus.RESOLVED, IncidentStatus.SUPPRESSED},
    IncidentStatus.ACKNOWLEDGED: {IncidentStatus.MONITORING, IncidentStatus.RESOLVED, IncidentStatus.SUPPRESSED},
    IncidentStatus.MONITORING: {IncidentStatus.OPEN, IncidentStatus.RESOLVED, IncidentStatus.SUPPRESSED},
    IncidentStatus.RESOLVED: {IncidentStatus.OPEN},
    IncidentStatus.SUPPRESSED: {IncidentStatus.OPEN, IncidentStatus.RESOLVED},
}
SEVERITY_RANK = {Severity.INFO.value: 0, Severity.WARNING.value: 1, Severity.CRITICAL.value: 2}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_utc(moment: datetime | None) -> datetime:
    value = moment or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return _ensure_utc(value)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        return _ensure_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _safe_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)


def _json_hash(value: Any) -> str:
    return hashlib.sha256(_safe_json(value).encode("utf-8")).hexdigest()


def incident_id_for(deduplication_key: str) -> str:
    return "inc_" + hashlib.sha256(deduplication_key.encode("utf-8")).hexdigest()[:16]


def event_id_for(incident_id: str, event_type: str, fingerprint: str, created_at: str) -> str:
    seed = f"{incident_id}|{event_type}|{fingerprint}|{created_at}"
    return "evt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class RuleSettings:
    enabled: bool
    version: str
    healthy_observations_to_resolve: int = 2
    warning_after_seconds: dict[str, int] = field(default_factory=dict)
    critical_after_seconds: dict[str, int] = field(default_factory=dict)
    startup_grace_seconds: int = 0
    minimum_eligible_trips: int = 5
    warning_below_percentage: float = 80.0
    critical_below_percentage: float = 50.0
    healthy_at_or_above_percentage: float = 90.0
    critical_headway_ratio: float = 3.0
    minimum_coverage_percentage: float = 60.0
    confidence_statuses: tuple[str, ...] = ("HIGH", "OBSERVED", "OK")


@dataclass(frozen=True)
class IncidentRuleConfig:
    stale_feed: RuleSettings
    low_realtime_coverage: RuleSettings
    severe_service_gap: RuleSettings
    blocking_quality_failure: RuleSettings
    stale_serving_artifact: RuleSettings
    source_overrides: dict[str, dict[str, RuleSettings]] = field(default_factory=dict)

    def for_source(self, source: str) -> IncidentRuleConfig:
        overrides = self.source_overrides.get(source, {})
        return IncidentRuleConfig(
            stale_feed=overrides.get("stale_feed", self.stale_feed),
            low_realtime_coverage=overrides.get("low_realtime_coverage", self.low_realtime_coverage),
            severe_service_gap=overrides.get("severe_service_gap", self.severe_service_gap),
            blocking_quality_failure=overrides.get("blocking_quality_failure", self.blocking_quality_failure),
            stale_serving_artifact=overrides.get("stale_serving_artifact", self.stale_serving_artifact),
        )


@dataclass(frozen=True)
class IncidentCandidate:
    candidate_key: str
    rule_id: str
    rule_version: str
    source: str
    feed_type: str | None
    entity_type: str
    entity_id: str
    service_date: str | None
    period_start: str | None
    period_end: str | None
    observed_at: str
    metric_name: str
    metric_value: float | None
    warning_threshold: float | None
    critical_threshold: float | None
    healthy_threshold: float | None
    candidate_state: CandidateState
    suggested_severity: Severity | None
    confidence: str | None
    coverage: float | None
    calculation_version: str | None
    serving_run_id: str | None
    evidence: dict[str, Any]

    @property
    def evidence_fingerprint(self) -> str:
        payload = asdict(self)
        payload.pop("observed_at", None)
        payload["evidence"].pop("correlation_id", None)
        return _json_hash(payload)


@dataclass(frozen=True)
class TransitionSummary:
    candidate_key: str
    action: str
    incident_id: str | None = None
    event_type: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    evaluation_run_id: str
    correlation_id: str
    status: str
    source_filter: str | None
    serving_run_id: str | None
    rule_versions: dict[str, str]
    candidate_count: int
    opened_count: int = 0
    updated_count: int = 0
    escalated_count: int = 0
    resolved_count: int = 0
    reopened_count: int = 0
    suppressed_count: int = 0
    skipped_count: int = 0
    transitions: list[TransitionSummary] = field(default_factory=list)
    dry_run: bool = False
    error_summary: str | None = None


class IncidentRepository(Protocol):
    def migrate(self) -> None: ...
    def schema_version(self) -> int: ...
    def target_label(self) -> str: ...
    def transaction(self) -> contextlib.AbstractContextManager[Any]: ...
    def _row_to_dict(self, row: Any) -> dict[str, Any]: ...
    def get_by_id(self, incident_id: str) -> dict[str, Any] | None: ...
    def get_active_by_deduplication_key(self, deduplication_key: str) -> dict[str, Any] | None: ...
    def get_by_deduplication_key(self, deduplication_key: str) -> dict[str, Any] | None: ...
    def list_incidents(self, **filters: Any) -> list[dict[str, Any]]: ...
    def list_events(self, incident_id: str | None = None, *, limit: int = 500) -> list[dict[str, Any]]: ...
    def list_evaluation_runs(self, *, source: str | None = None, limit: int = 100) -> list[dict[str, Any]]: ...
    def upsert_incident(self, connection: Any, incident: dict[str, Any]) -> None: ...
    def append_event(self, connection: Any, event: dict[str, Any]) -> None: ...
    def acquire_evaluation_lock(self, scope: str, owner: str, now: datetime, *, ttl_seconds: int = 900) -> bool: ...
    def release_evaluation_lock(self, scope: str, owner: str) -> None: ...
    def record_evaluation_run(self, result: EvaluationResult, *, started_at: str, completed_at: str | None = None) -> None: ...


def default_rule_config() -> IncidentRuleConfig:
    config = IncidentRuleConfig(
        stale_feed=RuleSettings(
            enabled=True,
            version="stale_feed_v1",
            healthy_observations_to_resolve=2,
            warning_after_seconds={"trip_updates": 90, "vehicle_positions": 90, "service_alerts": 600},
            critical_after_seconds={"trip_updates": 300, "vehicle_positions": 300, "service_alerts": 1800},
            startup_grace_seconds=120,
        ),
        low_realtime_coverage=RuleSettings(
            enabled=True,
            version="low_coverage_v1",
            healthy_observations_to_resolve=2,
            minimum_eligible_trips=5,
            warning_below_percentage=80.0,
            critical_below_percentage=50.0,
            healthy_at_or_above_percentage=90.0,
            confidence_statuses=("HIGH", "OBSERVED"),
        ),
        severe_service_gap=RuleSettings(
            enabled=True,
            version="service_gap_v1",
            healthy_observations_to_resolve=2,
            critical_headway_ratio=3.0,
            minimum_coverage_percentage=60.0,
            confidence_statuses=("HIGH", "OBSERVED", "VEHICLE_POSITION_PASSAGE", "TRIP_UPDATE_APPROXIMATION"),
        ),
        blocking_quality_failure=RuleSettings(enabled=True, version="quality_failure_v1", healthy_observations_to_resolve=1),
        stale_serving_artifact=RuleSettings(
            enabled=True,
            version="stale_serving_v1",
            healthy_observations_to_resolve=2,
            warning_after_seconds={"artifact": 1200},
            critical_after_seconds={"artifact": 3600},
            startup_grace_seconds=120,
        ),
    )
    override_text = os.getenv("MCT_INCIDENT_RULES_JSON")
    if override_text:
        config = _merge_rule_overrides(config, json.loads(override_text))
    validate_rule_config(config)
    return config


def _settings_from_dict(base: RuleSettings, values: dict[str, Any]) -> RuleSettings:
    payload = asdict(base)
    payload.update(values)
    if isinstance(payload.get("confidence_statuses"), list):
        payload["confidence_statuses"] = tuple(payload["confidence_statuses"])
    return RuleSettings(**payload)


def _merge_rule_overrides(base: IncidentRuleConfig, values: dict[str, Any]) -> IncidentRuleConfig:
    rules = {
        name: getattr(base, name)
        for name in ("stale_feed", "low_realtime_coverage", "severe_service_gap", "blocking_quality_failure", "stale_serving_artifact")
    }
    for name, override in values.get("incident_rules", values).items():
        if name in rules and isinstance(override, dict):
            rules[name] = _settings_from_dict(rules[name], override)
    source_overrides: dict[str, dict[str, RuleSettings]] = {}
    for source, source_values in values.get("source_overrides", {}).items():
        source_overrides[source] = {}
        for name, override in source_values.items():
            if name in rules and isinstance(override, dict):
                source_overrides[source][name] = _settings_from_dict(rules[name], override)
    return IncidentRuleConfig(**rules, source_overrides=source_overrides)


def validate_rule_config(config: IncidentRuleConfig) -> None:
    for rule in (config.stale_feed, config.low_realtime_coverage, config.severe_service_gap, config.blocking_quality_failure, config.stale_serving_artifact):
        if rule.healthy_observations_to_resolve < 1:
            raise ValueError(f"{rule.version}: healthy_observations_to_resolve must be positive")
        if rule.startup_grace_seconds < 0:
            raise ValueError(f"{rule.version}: startup_grace_seconds must be non-negative")
        for mapping_name in ("warning_after_seconds", "critical_after_seconds"):
            for value in getattr(rule, mapping_name).values():
                if value < 0:
                    raise ValueError(f"{rule.version}: durations must be non-negative")
        for feed_type, warning in rule.warning_after_seconds.items():
            critical = rule.critical_after_seconds.get(feed_type)
            if critical is not None and warning >= critical:
                raise ValueError(f"{rule.version}: warning threshold must be less severe than critical threshold")
    low = config.low_realtime_coverage
    if low.critical_below_percentage >= low.warning_below_percentage:
        raise ValueError("low_coverage_v1: critical threshold must be below warning threshold")
    if low.healthy_at_or_above_percentage <= low.warning_below_percentage:
        raise ValueError("low_coverage_v1: healthy threshold must be above warning threshold")
    if low.minimum_eligible_trips < 0 or config.severe_service_gap.minimum_coverage_percentage < 0:
        raise ValueError("incident rule thresholds must be non-negative")


class SQLiteIncidentRepository:
    """SQLite repository used for local mode and deterministic tests."""

    def __init__(self, root: Path = Path("data/incidents")) -> None:
        self.root = root
        self.db_path = root / "incidents.sqlite"
        self.events_path = root / "incident_events.jsonl"

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.root.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=60, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with contextlib.suppress(sqlite3.OperationalError):
            connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
        finally:
            connection.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def migrate(self) -> None:
        with self.transaction() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_versions (component TEXT PRIMARY KEY, version INTEGER NOT NULL, updated_at TEXT NOT NULL)")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    deduplication_key TEXT NOT NULL UNIQUE,
                    rule_id TEXT NOT NULL,
                    rule_version TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    feed_type TEXT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    service_date TEXT,
                    operational_period_start TEXT,
                    operational_period_end TEXT,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    first_observed_at TEXT NOT NULL,
                    last_observed_at TEXT NOT NULL,
                    last_evaluated_at TEXT NOT NULL,
                    healthy_since TEXT,
                    healthy_observation_count INTEGER NOT NULL DEFAULT 0,
                    acknowledged_at TEXT,
                    acknowledged_by TEXT,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    suppressed_at TEXT,
                    suppressed_by TEXT,
                    suppression_expires_at TEXT,
                    manual_resolution INTEGER NOT NULL DEFAULT 0,
                    manual_resolution_note TEXT,
                    occurrence_count INTEGER NOT NULL DEFAULT 1,
                    recurrence_count INTEGER NOT NULL DEFAULT 0,
                    evidence_version INTEGER NOT NULL DEFAULT 1,
                    latest_evidence TEXT NOT NULL,
                    evidence_fingerprint TEXT NOT NULL,
                    calculation_version TEXT,
                    serving_run_id TEXT,
                    correlation_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_events (
                    event_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    event_type TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT,
                    previous_severity TEXT,
                    new_severity TEXT,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    reason TEXT,
                    evidence TEXT,
                    rule_id TEXT,
                    rule_version TEXT,
                    correlation_id TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_evaluation_runs (
                    evaluation_run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    source_filter TEXT,
                    serving_run_id TEXT,
                    rule_versions TEXT NOT NULL,
                    candidate_count INTEGER NOT NULL DEFAULT 0,
                    opened_count INTEGER NOT NULL DEFAULT 0,
                    updated_count INTEGER NOT NULL DEFAULT 0,
                    escalated_count INTEGER NOT NULL DEFAULT 0,
                    resolved_count INTEGER NOT NULL DEFAULT 0,
                    reopened_count INTEGER NOT NULL DEFAULT 0,
                    suppressed_count INTEGER NOT NULL DEFAULT 0,
                    skipped_count INTEGER NOT NULL DEFAULT 0,
                    error_summary TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_evaluation_locks (
                    scope TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO schema_versions(component, version, updated_at) VALUES('incidents', ?, ?)",
                (INCIDENT_SCHEMA_VERSION, utc_now()),
            )

    def schema_version(self) -> int:
        if not self.db_path.exists():
            return 0
        with self._connect() as connection:
            with contextlib.suppress(sqlite3.Error):
                row = connection.execute("SELECT version FROM schema_versions WHERE component = 'incidents'").fetchone()
                return int(row["version"]) if row else 0
        return 0

    def target_label(self) -> str:
        return str(self.db_path)

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["latest_evidence"] = json.loads(payload.pop("latest_evidence"))
        payload["evidence"] = payload["latest_evidence"]
        payload["observation_count"] = payload["occurrence_count"]
        if "manual_resolution" in payload:
            payload["manual_resolution"] = bool(payload["manual_resolution"])
        return payload

    def _event_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = dict(row)
        payload["evidence"] = json.loads(payload["evidence"]) if payload.get("evidence") else None
        return payload

    def get_by_id(self, incident_id: str) -> dict[str, Any] | None:
        self.migrate()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_active_by_deduplication_key(self, deduplication_key: str) -> dict[str, Any] | None:
        self.migrate()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM incidents WHERE deduplication_key = ? AND status IN ('OPEN','ACKNOWLEDGED','MONITORING','SUPPRESSED')",
                (deduplication_key,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_deduplication_key(self, deduplication_key: str) -> dict[str, Any] | None:
        self.migrate()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE deduplication_key = ?", (deduplication_key,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_incidents(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        rule_id: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        self.migrate()
        sql = "SELECT * FROM incidents WHERE 1=1"
        params: list[Any] = []
        for column, value in (("status", status), ("source", source), ("rule_id", rule_id), ("severity", severity)):
            if value:
                sql += f" AND {column} = ?"
                params.append(value)
        sql += " ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'WARNING' THEN 1 ELSE 2 END, updated_at DESC LIMIT ? OFFSET ?"
        params.extend([max(1, min(limit, 500)), max(0, offset)])
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_events(self, incident_id: str | None = None, *, limit: int = 500) -> list[dict[str, Any]]:
        self.migrate()
        sql = "SELECT * FROM incident_events"
        params: list[Any] = []
        if incident_id:
            sql += " WHERE incident_id = ?"
            params.append(incident_id)
        sql += " ORDER BY created_at ASC, rowid ASC LIMIT ?"
        params.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._event_row_to_dict(row) for row in rows]

    def list_evaluation_runs(self, *, source: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self.migrate()
        sql = "SELECT * FROM incident_evaluation_runs WHERE 1=1"
        params: list[Any] = []
        if source:
            sql += " AND source_filter = ?"
            params.append(source)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        result = []
        for row in rows:
            payload = dict(row)
            payload["rule_versions"] = json.loads(payload["rule_versions"])
            result.append(payload)
        return result

    def upsert_incident(self, connection: Any, incident: dict[str, Any]) -> None:
        columns = [key for key in incident if key != "evidence"]
        values = [incident[key] for key in columns]
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(f"{column}=excluded.{column}" for column in columns if column != "incident_id")
        connection.execute(
            f"INSERT INTO incidents ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(incident_id) DO UPDATE SET {assignments}",
            values,
        )

    def append_event(self, connection: Any, event: dict[str, Any]) -> None:
        columns = list(event)
        placeholders = ", ".join("?" for _ in columns)
        connection.execute(f"INSERT INTO incident_events ({', '.join(columns)}) VALUES ({placeholders})", [event[column] for column in columns])
        self._append_jsonl_event(event)

    def _append_jsonl_event(self, event: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        payload["evidence"] = json.loads(payload["evidence"]) if payload.get("evidence") else None
        payload["operator"] = payload["actor_id"]
        payload["note"] = payload.get("reason")
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n")

    def acquire_evaluation_lock(self, scope: str, owner: str, now: datetime, *, ttl_seconds: int = 900) -> bool:
        self.migrate()
        now_text = _ensure_utc(now).isoformat()
        expires_at = (_ensure_utc(now) + timedelta(seconds=ttl_seconds)).isoformat()
        with self.transaction() as connection:
            row = connection.execute("SELECT owner, expires_at FROM incident_evaluation_locks WHERE scope = ?", (scope,)).fetchone()
            if row and row["expires_at"] > now_text and row["owner"] != owner:
                return False
            connection.execute(
                "INSERT OR REPLACE INTO incident_evaluation_locks(scope, owner, acquired_at, expires_at) VALUES (?, ?, ?, ?)",
                (scope, owner, now_text, expires_at),
            )
        return True

    def release_evaluation_lock(self, scope: str, owner: str) -> None:
        self.migrate()
        with self.transaction() as connection:
            connection.execute("DELETE FROM incident_evaluation_locks WHERE scope = ? AND owner = ?", (scope, owner))

    def record_evaluation_run(self, result: EvaluationResult, *, started_at: str, completed_at: str | None = None) -> None:
        self.migrate()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO incident_evaluation_runs (
                    evaluation_run_id, correlation_id, started_at, completed_at, status, source_filter, serving_run_id,
                    rule_versions, candidate_count, opened_count, updated_count, escalated_count, resolved_count,
                    reopened_count, suppressed_count, skipped_count, error_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.evaluation_run_id,
                    result.correlation_id,
                    started_at,
                    completed_at,
                    result.status,
                    result.source_filter,
                    result.serving_run_id,
                    _safe_json(result.rule_versions),
                    result.candidate_count,
                    result.opened_count,
                    result.updated_count,
                    result.escalated_count,
                    result.resolved_count,
                    result.reopened_count,
                    result.suppressed_count,
                    result.skipped_count,
                    result.error_summary,
                ),
            )


class _PostgresCursorAdapter:  # pragma: no cover - covered by PostgreSQL integration tests
    def __init__(self, cursor: Any) -> None:
        self.cursor = cursor

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> _PostgresCursorAdapter:
        self.cursor.execute(sql.replace("?", "%s"), params)
        return self

    def fetchone(self) -> Any:
        return self.cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return list(self.cursor.fetchall())


class PostgresIncidentRepository:  # pragma: no cover - covered by PostgreSQL integration tests
    """PostgreSQL repository used by Compose and production runtime."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("MCT_INCIDENT_DATABASE_URL", "")
        if not self.database_url:
            raise RuntimeError("MCT_INCIDENT_DATABASE_URL is required when MCT_INCIDENT_BACKEND=postgres")
        self.events_path = Path(os.getenv("MCT_INCIDENT_EVENT_JSONL", "data/incidents/incident_events.jsonl"))

    def _connect_raw(self) -> Any:
        import psycopg2
        import psycopg2.extras

        return psycopg2.connect(self.database_url, cursor_factory=psycopg2.extras.RealDictCursor)

    @contextlib.contextmanager
    def transaction(self) -> Iterator[_PostgresCursorAdapter]:
        connection = self._connect_raw()
        try:
            with connection.cursor() as cursor:
                yield _PostgresCursorAdapter(cursor)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[_PostgresCursorAdapter]:
        connection = self._connect_raw()
        try:
            with connection.cursor() as cursor:
                yield _PostgresCursorAdapter(cursor)
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_versions (component TEXT PRIMARY KEY, version INTEGER NOT NULL, updated_at TIMESTAMPTZ NOT NULL)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    deduplication_key TEXT NOT NULL UNIQUE,
                    rule_id TEXT NOT NULL,
                    rule_version TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    feed_type TEXT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    service_date TEXT,
                    operational_period_start TIMESTAMPTZ,
                    operational_period_end TIMESTAMPTZ,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    opened_at TIMESTAMPTZ NOT NULL,
                    first_observed_at TIMESTAMPTZ NOT NULL,
                    last_observed_at TIMESTAMPTZ NOT NULL,
                    last_evaluated_at TIMESTAMPTZ NOT NULL,
                    healthy_since TIMESTAMPTZ,
                    healthy_observation_count INTEGER NOT NULL DEFAULT 0,
                    acknowledged_at TIMESTAMPTZ,
                    acknowledged_by TEXT,
                    resolved_at TIMESTAMPTZ,
                    resolved_by TEXT,
                    suppressed_at TIMESTAMPTZ,
                    suppressed_by TEXT,
                    suppression_expires_at TIMESTAMPTZ,
                    manual_resolution BOOLEAN NOT NULL DEFAULT FALSE,
                    manual_resolution_note TEXT,
                    occurrence_count INTEGER NOT NULL DEFAULT 1,
                    recurrence_count INTEGER NOT NULL DEFAULT 0,
                    evidence_version INTEGER NOT NULL DEFAULT 1,
                    latest_evidence JSONB NOT NULL,
                    evidence_fingerprint TEXT NOT NULL,
                    calculation_version TEXT,
                    serving_run_id TEXT,
                    correlation_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_events (
                    event_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
                    event_type TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT,
                    previous_severity TEXT,
                    new_severity TEXT,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    reason TEXT,
                    evidence JSONB,
                    rule_id TEXT,
                    rule_version TEXT,
                    correlation_id TEXT,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_evaluation_runs (
                    evaluation_run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL,
                    completed_at TIMESTAMPTZ,
                    status TEXT NOT NULL,
                    source_filter TEXT,
                    serving_run_id TEXT,
                    rule_versions JSONB NOT NULL,
                    candidate_count INTEGER NOT NULL DEFAULT 0,
                    opened_count INTEGER NOT NULL DEFAULT 0,
                    updated_count INTEGER NOT NULL DEFAULT 0,
                    escalated_count INTEGER NOT NULL DEFAULT 0,
                    resolved_count INTEGER NOT NULL DEFAULT 0,
                    reopened_count INTEGER NOT NULL DEFAULT 0,
                    suppressed_count INTEGER NOT NULL DEFAULT 0,
                    skipped_count INTEGER NOT NULL DEFAULT 0,
                    error_summary TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_evaluation_locks (
                    scope TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    acquired_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            for statement in (
                "CREATE INDEX IF NOT EXISTS idx_incidents_source ON incidents(source)",
                "CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)",
                "CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity)",
                "CREATE INDEX IF NOT EXISTS idx_incidents_rule_id ON incidents(rule_id)",
                "CREATE INDEX IF NOT EXISTS idx_incidents_opened_at ON incidents(opened_at)",
                "CREATE INDEX IF NOT EXISTS idx_incident_events_incident_created ON incident_events(incident_id, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_incident_evaluation_runs_status_started ON incident_evaluation_runs(status, started_at)",
            ):
                connection.execute(statement)
            connection.execute(
                """
                INSERT INTO schema_versions(component, version, updated_at)
                VALUES('incidents', ?, ?)
                ON CONFLICT(component) DO UPDATE SET version = EXCLUDED.version, updated_at = EXCLUDED.updated_at
                """,
                (INCIDENT_SCHEMA_VERSION, utc_now()),
            )

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT version FROM schema_versions WHERE component = 'incidents'").fetchone()
        return int(row["version"]) if row else 0

    def target_label(self) -> str:
        parsed = urlsplit(str(self.database_url))
        netloc = str(parsed.hostname or "")
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((str(parsed.scheme), netloc, str(parsed.path), "", ""))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = dict(row)
        payload["latest_evidence"] = _json_value(payload["latest_evidence"])
        payload["evidence"] = payload["latest_evidence"]
        payload["observation_count"] = payload["occurrence_count"]
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = _ensure_utc(value).isoformat()
        if "manual_resolution" in payload:
            payload["manual_resolution"] = bool(payload["manual_resolution"])
        return payload

    def _event_row_to_dict(self, row: Any) -> dict[str, Any]:
        payload = dict(row)
        payload["evidence"] = _json_value(payload.get("evidence")) if payload.get("evidence") is not None else None
        if isinstance(payload.get("created_at"), datetime):
            payload["created_at"] = _ensure_utc(payload["created_at"]).isoformat()
        return payload

    def get_by_id(self, incident_id: str) -> dict[str, Any] | None:
        self.migrate()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def get_active_by_deduplication_key(self, deduplication_key: str) -> dict[str, Any] | None:
        self.migrate()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM incidents WHERE deduplication_key = ? AND status IN ('OPEN','ACKNOWLEDGED','MONITORING','SUPPRESSED')",
                (deduplication_key,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def get_by_deduplication_key(self, deduplication_key: str) -> dict[str, Any] | None:
        self.migrate()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE deduplication_key = ?", (deduplication_key,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_incidents(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        rule_id: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        self.migrate()
        sql = "SELECT * FROM incidents WHERE 1=1"
        params: list[Any] = []
        for column, value in (("status", status), ("source", source), ("rule_id", rule_id), ("severity", severity)):
            if value:
                sql += f" AND {column} = ?"
                params.append(value)
        sql += " ORDER BY CASE severity WHEN 'CRITICAL' THEN 0 WHEN 'WARNING' THEN 1 ELSE 2 END, updated_at DESC LIMIT ? OFFSET ?"
        params.extend([max(1, min(limit, 500)), max(0, offset)])
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_events(self, incident_id: str | None = None, *, limit: int = 500) -> list[dict[str, Any]]:
        self.migrate()
        sql = "SELECT * FROM incident_events"
        params: list[Any] = []
        if incident_id:
            sql += " WHERE incident_id = ?"
            params.append(incident_id)
        sql += " ORDER BY created_at ASC, event_id ASC LIMIT ?"
        params.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._event_row_to_dict(row) for row in rows]

    def list_evaluation_runs(self, *, source: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        self.migrate()
        sql = "SELECT * FROM incident_evaluation_runs WHERE 1=1"
        params: list[Any] = []
        if source:
            sql += " AND source_filter = ?"
            params.append(source)
        sql += " ORDER BY started_at DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        result = []
        for row in rows:
            payload = dict(row)
            payload["rule_versions"] = _json_value(payload["rule_versions"])
            for key, value in list(payload.items()):
                if isinstance(value, datetime):
                    payload[key] = _ensure_utc(value).isoformat()
            result.append(payload)
        return result

    def upsert_incident(self, connection: Any, incident: dict[str, Any]) -> None:
        columns = [key for key in incident if key != "evidence"]
        values = [_pg_value(incident[key]) for key in columns]
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(f"{column}=EXCLUDED.{column}" for column in columns if column != "incident_id")
        connection.execute(
            f"INSERT INTO incidents ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT(incident_id) DO UPDATE SET {assignments}",
            values,
        )

    def append_event(self, connection: Any, event: dict[str, Any]) -> None:
        columns = list(event)
        placeholders = ", ".join("?" for _ in columns)
        connection.execute(f"INSERT INTO incident_events ({', '.join(columns)}) VALUES ({placeholders})", [_pg_value(event[column]) for column in columns])
        self._append_jsonl_event(event)

    def _append_jsonl_event(self, event: dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        payload["evidence"] = _json_value(payload.get("evidence")) if payload.get("evidence") else None
        payload["operator"] = payload["actor_id"]
        payload["note"] = payload.get("reason")
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n")

    def acquire_evaluation_lock(self, scope: str, owner: str, now: datetime, *, ttl_seconds: int = 900) -> bool:
        self.migrate()
        now_text = _ensure_utc(now).isoformat()
        expires_at = (_ensure_utc(now) + timedelta(seconds=ttl_seconds)).isoformat()
        with self.transaction() as connection:
            row = connection.execute("SELECT owner, expires_at FROM incident_evaluation_locks WHERE scope = ? FOR UPDATE", (scope,)).fetchone()
            row_expires = _parse_datetime(row["expires_at"]) if row else None
            if row and row_expires and row_expires > _ensure_utc(now) and row["owner"] != owner:
                return False
            connection.execute(
                """
                INSERT INTO incident_evaluation_locks(scope, owner, acquired_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(scope) DO UPDATE SET owner = EXCLUDED.owner, acquired_at = EXCLUDED.acquired_at, expires_at = EXCLUDED.expires_at
                """,
                (scope, owner, now_text, expires_at),
            )
        return True

    def release_evaluation_lock(self, scope: str, owner: str) -> None:
        self.migrate()
        with self.transaction() as connection:
            connection.execute("DELETE FROM incident_evaluation_locks WHERE scope = ? AND owner = ?", (scope, owner))

    def record_evaluation_run(self, result: EvaluationResult, *, started_at: str, completed_at: str | None = None) -> None:
        self.migrate()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO incident_evaluation_runs (
                    evaluation_run_id, correlation_id, started_at, completed_at, status, source_filter, serving_run_id,
                    rule_versions, candidate_count, opened_count, updated_count, escalated_count, resolved_count,
                    reopened_count, suppressed_count, skipped_count, error_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evaluation_run_id) DO UPDATE SET
                    completed_at = EXCLUDED.completed_at,
                    status = EXCLUDED.status,
                    serving_run_id = EXCLUDED.serving_run_id,
                    rule_versions = EXCLUDED.rule_versions,
                    candidate_count = EXCLUDED.candidate_count,
                    opened_count = EXCLUDED.opened_count,
                    updated_count = EXCLUDED.updated_count,
                    escalated_count = EXCLUDED.escalated_count,
                    resolved_count = EXCLUDED.resolved_count,
                    reopened_count = EXCLUDED.reopened_count,
                    suppressed_count = EXCLUDED.suppressed_count,
                    skipped_count = EXCLUDED.skipped_count,
                    error_summary = EXCLUDED.error_summary
                """,
                (
                    result.evaluation_run_id,
                    result.correlation_id,
                    started_at,
                    completed_at,
                    result.status,
                    result.source_filter,
                    result.serving_run_id,
                    _safe_json(result.rule_versions),
                    result.candidate_count,
                    result.opened_count,
                    result.updated_count,
                    result.escalated_count,
                    result.resolved_count,
                    result.reopened_count,
                    result.suppressed_count,
                    result.skipped_count,
                    result.error_summary,
                ),
            )


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _pg_value(value: Any) -> Any:
    if isinstance(value, str):
        with contextlib.suppress(ValueError):
            parsed = json.loads(value)
            if isinstance(parsed, (dict, list)):
                import psycopg2.extras

                return psycopg2.extras.Json(parsed)
        parsed_dt = _parse_datetime(value)
        if parsed_dt and ("T" in value or value.endswith("+00:00")):
            return parsed_dt
    return value


def incident_backend() -> str:
    backend = os.getenv("MCT_INCIDENT_BACKEND", "sqlite").strip().lower()
    if backend not in {"sqlite", "postgres"}:
        raise ValueError("MCT_INCIDENT_BACKEND must be sqlite or postgres")
    if os.getenv("MCT_ENV") == "production" and backend == "sqlite" and os.getenv("MCT_ALLOW_SQLITE_IN_PRODUCTION") != "true":
        raise RuntimeError("SQLite incident backend is not allowed in production without MCT_ALLOW_SQLITE_IN_PRODUCTION=true")
    return backend


def incident_repository(root: Path = DEFAULT_INCIDENT_ROOT) -> IncidentRepository:
    repository = PostgresIncidentRepository() if incident_backend() == "postgres" else SQLiteIncidentRepository(root)
    return cast(IncidentRepository, repository)


class IncidentStore:
    """Compatibility facade over the configured incident repository."""

    def __init__(self, root: Path = DEFAULT_INCIDENT_ROOT) -> None:
        self.root = root
        self.path = root / "incidents.json"
        self.events_path = root / "incident_events.jsonl"
        self.repository: IncidentRepository = incident_repository(root)
        self.repository.migrate()

    def _read(self) -> list[dict[str, Any]]:
        return self.repository.list_incidents(limit=500)

    def _write(self, incidents: list[dict[str, Any]]) -> None:
        with self.repository.transaction() as connection:
            for incident in incidents:
                payload = _normalize_incident_payload(incident)
                self.repository.upsert_incident(connection, payload)

    def list_incidents(self, *, status: str | None = None, source: str | None = None, limit: int = 100, **filters: Any) -> list[dict[str, Any]]:
        return self.repository.list_incidents(status=status, source=source, limit=limit, **filters)

    def list_events(self, incident_id: str | None = None, *, limit: int = 500) -> list[dict[str, Any]]:
        return self.repository.list_events(incident_id, limit=limit)

    def get_by_id(self, incident_id: str) -> dict[str, Any] | None:
        return self.repository.get_by_id(incident_id)

    def list_evaluation_runs(self, *, source: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return self.repository.list_evaluation_runs(source=source, limit=limit)

    def open_or_update(
        self,
        *,
        rule_id: str,
        rule_version: str,
        source: str,
        entity_type: str,
        entity_id: str,
        severity: str,
        title: str,
        summary: str,
        evidence: dict[str, Any],
        incident_type: str | None = None,
        deduplication_key: str | None = None,
    ) -> dict[str, Any]:
        now = _ensure_utc(None)
        period = evidence.get("service_date") or evidence.get("period") or "current"
        dedupe = deduplication_key or f"{rule_id}:{source}:{entity_type}:{entity_id}:{period}"
        candidate = IncidentCandidate(
            candidate_key=dedupe,
            rule_id=rule_id,
            rule_version=rule_version,
            source=source,
            feed_type=evidence.get("feed_type"),
            entity_type=entity_type,
            entity_id=entity_id,
            service_date=evidence.get("service_date"),
            period_start=evidence.get("period_start"),
            period_end=evidence.get("period_end"),
            observed_at=now.isoformat(),
            metric_name=str(evidence.get("metric_name", rule_id)),
            metric_value=_float_or_none(evidence.get("metric_value")),
            warning_threshold=_float_or_none(evidence.get("warning_threshold")),
            critical_threshold=_float_or_none(evidence.get("critical_threshold")),
            healthy_threshold=_float_or_none(evidence.get("healthy_threshold")),
            candidate_state=CandidateState.UNHEALTHY,
            suggested_severity=Severity(severity),
            confidence=evidence.get("confidence"),
            coverage=_float_or_none(evidence.get("coverage")),
            calculation_version=evidence.get("calculation_version"),
            serving_run_id=evidence.get("serving_run_id"),
            evidence=evidence,
        )
        engine = IncidentEvaluationEngine(repository=self.repository, rule_config=default_rule_config())
        engine.apply_candidate(candidate, now=now, correlation_id=str(evidence.get("correlation_id") or "manual-open-or-update"))
        incident = self.repository.get_by_deduplication_key(dedupe)
        if incident is None:
            raise RuntimeError("incident was not persisted")
        if title != incident["title"] or summary != incident["summary"] or (incident_type and incident_type != incident["incident_type"]):
            with self.repository.transaction() as connection:
                incident.update({"title": title, "summary": summary, "incident_type": incident_type or rule_id, "updated_at": now.isoformat()})
                self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
            incident = self.repository.get_by_deduplication_key(dedupe)
        return incident or {}

    def transition(
        self,
        incident_id: str,
        *,
        status: str,
        operator: str,
        note: str | None = None,
        suppress_until: str | None = None,
    ) -> dict[str, Any]:
        target = IncidentStatus(status)
        incident = self.repository.get_by_id(incident_id)
        if incident is None:
            raise KeyError(f"Incident not found: {incident_id}")
        current = IncidentStatus(incident["status"])
        if target != current and target not in VALID_TRANSITIONS[current]:
            raise ValueError(f"Invalid incident transition {current.value} -> {target.value}")
        if target == IncidentStatus.RESOLVED and not (note and note.strip()):
            raise ValueError("Manual resolution requires a nonempty reason.")
        if target == current:
            return incident
        now = _ensure_utc(None).isoformat()
        event_type = {
            IncidentStatus.ACKNOWLEDGED: EventType.ACKNOWLEDGED,
            IncidentStatus.RESOLVED: EventType.MANUALLY_RESOLVED,
            IncidentStatus.SUPPRESSED: EventType.SUPPRESSED,
            IncidentStatus.OPEN: EventType.REOPENED,
            IncidentStatus.MONITORING: EventType.MONITORING_STARTED,
        }[target]
        updated = dict(incident)
        updated.update({"status": target.value, "updated_at": now, "last_evaluated_at": now})
        if target == IncidentStatus.ACKNOWLEDGED:
            updated.update({"acknowledged_at": now, "acknowledged_by": operator})
        if target == IncidentStatus.RESOLVED:
            updated.update({"resolved_at": now, "resolved_by": operator, "manual_resolution": True, "manual_resolution_note": note})
        if target == IncidentStatus.SUPPRESSED:
            expiry = _parse_datetime(suppress_until)
            if suppress_until and expiry is None:
                raise ValueError("Suppression expiry must be an ISO timestamp.")
            updated.update({"suppressed_at": now, "suppressed_by": operator, "suppression_expires_at": expiry.isoformat() if expiry else None})
        if target == IncidentStatus.OPEN:
            updated.update({"resolved_at": None, "resolved_by": None, "suppressed_at": None, "suppressed_by": None, "suppression_expires_at": None})
        with self.repository.transaction() as connection:
            self.repository.upsert_incident(connection, _normalize_incident_payload(updated))
            self.repository.append_event(
                connection,
                _make_event(
                    incident=incident,
                    event_type=event_type,
                    now=now,
                    previous_status=current.value,
                    new_status=target.value,
                    actor_type="operator",
                    actor_id=operator,
                    reason=note,
                    evidence=updated["latest_evidence"],
                    correlation_id=updated.get("correlation_id"),
                ),
            )
        return self.repository.get_by_id(incident_id) or updated

    def auto_resolve_healthy(self, *, healthy_after_seconds: int = 900) -> list[dict[str, Any]]:
        cutoff = _ensure_utc(None) - timedelta(seconds=healthy_after_seconds)
        resolved: list[dict[str, Any]] = []
        for incident in self.repository.list_incidents(limit=500):
            last = _parse_datetime(incident.get("last_observed_at"))
            if incident["status"] in OPEN_STATUSES and last and last < cutoff:
                resolved.append(self.transition(incident["incident_id"], status="RESOLVED", operator=SYSTEM_ACTOR, note="Legacy healthy timeout elapsed."))
        return resolved


class IncidentEvaluationEngine:
    def __init__(
        self,
        *,
        repository: IncidentRepository | None = None,
        rule_config: IncidentRuleConfig | None = None,
        serving_root: Path = Path("data/serving"),
        history_root: Path = Path("data/realtime_history"),
        quality_root: Path = Path("data/quality"),
        sources_config: Path = Path("config/sources.yml"),
    ) -> None:
        self.repository: IncidentRepository = repository or incident_repository()
        self.rule_config = rule_config or default_rule_config()
        self.serving_root = serving_root
        self.history_root = history_root
        self.quality_root = quality_root
        self.sources_config = sources_config
        self.repository.migrate()

    def evaluate(
        self,
        *,
        source: str | None = None,
        evaluation_time: datetime | None = None,
        correlation_id: str | None = None,
        dry_run: bool = False,
    ) -> EvaluationResult:
        now = _ensure_utc(evaluation_time)
        run_id = "eval_" + uuid.uuid4().hex[:16]
        corr = correlation_id or run_id
        scope = f"incidents:{source or 'all'}"
        serving_run_id: str | None = None
        rule_versions = {
            "stale_feed": self.rule_config.stale_feed.version,
            "low_realtime_coverage": self.rule_config.low_realtime_coverage.version,
            "severe_service_gap": self.rule_config.severe_service_gap.version,
            "blocking_quality_failure": self.rule_config.blocking_quality_failure.version,
            "stale_serving_artifact": self.rule_config.stale_serving_artifact.version,
        }
        started_at = now.isoformat()
        if not dry_run and not self.repository.acquire_evaluation_lock(scope, run_id, now):
            result = EvaluationResult(run_id, corr, "SKIPPED_LOCKED", source, None, rule_versions, 0, skipped_count=1)
            self.repository.record_evaluation_run(result, started_at=started_at, completed_at=now.isoformat())
            return result
        try:
            if not dry_run:
                self.repository.record_evaluation_run(EvaluationResult(run_id, corr, "STARTED", source, None, rule_versions, 0), started_at=started_at)
            candidates = self.load_candidates(source=source, evaluation_time=now, correlation_id=corr)
            serving_run_id = next((candidate.serving_run_id for candidate in candidates if candidate.serving_run_id), None)
            transitions: list[TransitionSummary] = []
            counts = {"opened": 0, "updated": 0, "escalated": 0, "resolved": 0, "reopened": 0, "suppressed": 0, "skipped": 0}
            for candidate in candidates:
                if dry_run:
                    transition = self.plan_candidate(candidate)
                else:
                    transition = self.apply_candidate(candidate, now=now, correlation_id=corr)
                transitions.append(transition)
                if transition.action in counts:
                    counts[transition.action] += 1
            result = EvaluationResult(
                run_id,
                corr,
                "SUCCESS",
                source,
                serving_run_id,
                rule_versions,
                len(candidates),
                opened_count=counts["opened"],
                updated_count=counts["updated"],
                escalated_count=counts["escalated"],
                resolved_count=counts["resolved"],
                reopened_count=counts["reopened"],
                suppressed_count=counts["suppressed"],
                skipped_count=counts["skipped"],
                transitions=transitions,
                dry_run=dry_run,
            )
            if not dry_run:
                self.repository.record_evaluation_run(result, started_at=started_at, completed_at=_ensure_utc(None).isoformat())
            return result
        except Exception as exc:
            result = EvaluationResult(run_id, corr, "FAILED", source, serving_run_id, rule_versions, 0, dry_run=dry_run, error_summary=str(exc)[:500])
            if not dry_run:
                self.repository.record_evaluation_run(result, started_at=started_at, completed_at=_ensure_utc(None).isoformat())
            raise
        finally:
            if not dry_run:
                self.repository.release_evaluation_lock(scope, run_id)

    def load_candidates(self, *, source: str | None, evaluation_time: datetime, correlation_id: str) -> list[IncidentCandidate]:
        sources = load_sources(self.sources_config)
        selected_sources = [source] if source else sorted(sources)
        candidates: list[IncidentCandidate] = []
        for source_id in selected_sources:
            if source_id not in sources:
                raise ValueError(f"Unknown source: {source_id}")
            config = self.rule_config.for_source(source_id)
            candidates.extend(_stale_feed_candidates(source_id, sources[source_id], config.stale_feed, self.history_root, evaluation_time, correlation_id))
            candidates.extend(_serving_artifact_candidates(source_id, config.stale_serving_artifact, self.serving_root, evaluation_time, correlation_id))
            candidates.extend(_quality_candidates(source_id, config.blocking_quality_failure, self.quality_root, evaluation_time, correlation_id))
            with contextlib.suppress(Exception):
                db_path = resolve_current_database(source_id, self.serving_root)
                pointer = read_current_pointer(source_id, self.serving_root)
                candidates.extend(_coverage_candidates(db_path, pointer, config.low_realtime_coverage, evaluation_time, correlation_id))
                candidates.extend(_service_gap_candidates(db_path, pointer, config.severe_service_gap, evaluation_time, correlation_id))
        return candidates

    def plan_candidate(self, candidate: IncidentCandidate) -> TransitionSummary:
        incident = self.repository.get_by_deduplication_key(candidate.candidate_key)
        if candidate.candidate_state in {CandidateState.NOT_APPLICABLE, CandidateState.NOT_ENOUGH_DATA, CandidateState.UNKNOWN}:
            return TransitionSummary(candidate.candidate_key, "skipped", incident.get("incident_id") if incident else None)
        if incident is None:
            return TransitionSummary(candidate.candidate_key, "opened")
        if candidate.candidate_state == CandidateState.HEALTHY:
            return TransitionSummary(candidate.candidate_key, "updated", incident["incident_id"], EventType.MONITORING_STARTED.value)
        if incident["status"] == IncidentStatus.RESOLVED.value:
            return TransitionSummary(candidate.candidate_key, "reopened", incident["incident_id"], EventType.REOPENED.value)
        return TransitionSummary(candidate.candidate_key, "updated", incident["incident_id"])

    def apply_candidate(self, candidate: IncidentCandidate, *, now: datetime, correlation_id: str) -> TransitionSummary:
        now_text = _ensure_utc(now).isoformat()
        if candidate.candidate_state in {CandidateState.NOT_APPLICABLE, CandidateState.NOT_ENOUGH_DATA}:
            return TransitionSummary(candidate.candidate_key, "skipped")
        with self.repository.transaction() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE deduplication_key = ?", (candidate.candidate_key,)).fetchone()
            incident = self.repository._row_to_dict(row) if row else None
            if candidate.candidate_state == CandidateState.UNKNOWN:
                if incident and incident["status"] in ACTIVE_STATUSES:
                    incident["last_evaluated_at"] = now_text
                    self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
                    return TransitionSummary(candidate.candidate_key, "updated", incident["incident_id"])
                return TransitionSummary(candidate.candidate_key, "skipped")
            if incident and incident["status"] == IncidentStatus.SUPPRESSED.value:
                expiry = _parse_datetime(incident.get("suppression_expires_at"))
                if expiry and expiry <= _ensure_utc(now):
                    event = EventType.SUPPRESSION_EXPIRED
                    incident.update(
                        {"status": IncidentStatus.OPEN.value if candidate.candidate_state == CandidateState.UNHEALTHY else IncidentStatus.RESOLVED.value}
                    )
                    incident.update({"suppressed_at": None, "suppressed_by": None, "suppression_expires_at": None, "updated_at": now_text})
                    self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
                    self.repository.append_event(
                        connection,
                        _make_event(
                            incident=incident,
                            event_type=event,
                            now=now_text,
                            previous_status="SUPPRESSED",
                            new_status=incident["status"],
                            actor_type="system",
                            actor_id=SYSTEM_ACTOR,
                            reason="Suppression expired.",
                            evidence=candidate.evidence,
                            correlation_id=correlation_id,
                        ),
                    )
                else:
                    incident["latest_evidence"] = candidate.evidence
                    incident["evidence_fingerprint"] = candidate.evidence_fingerprint
                    incident["last_evaluated_at"] = now_text
                    incident["updated_at"] = now_text
                    self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
                    return TransitionSummary(candidate.candidate_key, "suppressed", incident["incident_id"], EventType.EVALUATION_SKIPPED.value)
            if candidate.candidate_state == CandidateState.UNHEALTHY:
                if incident is None:
                    incident = _incident_from_candidate(candidate, now_text, correlation_id)
                    self.repository.upsert_incident(connection, incident)
                    self.repository.append_event(
                        connection,
                        _make_event(
                            incident=incident,
                            event_type=EventType.OPENED,
                            now=now_text,
                            previous_status=None,
                            new_status="OPEN",
                            actor_type="system",
                            actor_id=SYSTEM_ACTOR,
                            reason="Unhealthy authoritative evidence.",
                            evidence=candidate.evidence,
                            correlation_id=correlation_id,
                        ),
                    )
                    return TransitionSummary(candidate.candidate_key, "opened", incident["incident_id"], EventType.OPENED.value)
                if incident["status"] == IncidentStatus.RESOLVED.value:
                    previous = dict(incident)
                    incident.update(
                        {
                            "status": IncidentStatus.OPEN.value,
                            "severity": (candidate.suggested_severity or Severity.WARNING).value,
                            "resolved_at": None,
                            "resolved_by": None,
                            "manual_resolution": False,
                            "healthy_since": None,
                            "healthy_observation_count": 0,
                            "last_observed_at": candidate.observed_at,
                            "last_evaluated_at": now_text,
                            "latest_evidence": candidate.evidence,
                            "evidence_fingerprint": candidate.evidence_fingerprint,
                            "occurrence_count": int(incident["occurrence_count"]) + 1,
                            "recurrence_count": int(incident["recurrence_count"]) + 1,
                            "updated_at": now_text,
                        }
                    )
                    self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
                    self.repository.append_event(
                        connection,
                        _make_event(
                            incident=incident,
                            event_type=EventType.REOPENED,
                            now=now_text,
                            previous_status=previous["status"],
                            new_status="OPEN",
                            previous_severity=previous["severity"],
                            new_severity=incident["severity"],
                            actor_type="system",
                            actor_id=SYSTEM_ACTOR,
                            reason="Resolved condition returned.",
                            evidence=candidate.evidence,
                            correlation_id=correlation_id,
                        ),
                    )
                    return TransitionSummary(candidate.candidate_key, "reopened", incident["incident_id"], EventType.REOPENED.value)
                return self._apply_unhealthy(connection, incident, candidate, now_text, correlation_id)
            if candidate.candidate_state == CandidateState.HEALTHY and incident and incident["status"] in OPEN_STATUSES:
                return self._apply_healthy(connection, incident, candidate, now_text, correlation_id)
        return TransitionSummary(candidate.candidate_key, "skipped", incident.get("incident_id") if incident else None)

    def _apply_unhealthy(
        self,
        connection: Any,
        incident: dict[str, Any],
        candidate: IncidentCandidate,
        now_text: str,
        correlation_id: str,
    ) -> TransitionSummary:
        previous = dict(incident)
        new_severity = (candidate.suggested_severity or Severity.WARNING).value
        fingerprint_changed = incident.get("evidence_fingerprint") != candidate.evidence_fingerprint
        severity_changed = new_severity != incident["severity"]
        if not fingerprint_changed and not severity_changed and incident.get("last_evaluated_at") == now_text:
            return TransitionSummary(candidate.candidate_key, "skipped", incident["incident_id"])
        incident.update(
            {
                "last_observed_at": candidate.observed_at,
                "last_evaluated_at": now_text,
                "healthy_since": None,
                "healthy_observation_count": 0,
                "latest_evidence": candidate.evidence,
                "evidence_fingerprint": candidate.evidence_fingerprint,
                "calculation_version": candidate.calculation_version,
                "serving_run_id": candidate.serving_run_id,
                "occurrence_count": int(incident["occurrence_count"]) + (1 if fingerprint_changed else 0),
                "updated_at": now_text,
            }
        )
        if severity_changed:
            incident["severity"] = new_severity
        self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
        event_type = EventType.OBSERVED_AGAIN
        action = "updated"
        if severity_changed:
            event_type = EventType.SEVERITY_ESCALATED if SEVERITY_RANK[new_severity] > SEVERITY_RANK[previous["severity"]] else EventType.SEVERITY_DEESCALATED
            action = "escalated" if event_type == EventType.SEVERITY_ESCALATED else "updated"
        elif fingerprint_changed:
            event_type = EventType.EVIDENCE_UPDATED
        else:
            return TransitionSummary(candidate.candidate_key, "skipped", incident["incident_id"])
        self.repository.append_event(
            connection,
            _make_event(
                incident=incident,
                event_type=event_type,
                now=now_text,
                previous_status=previous["status"],
                new_status=incident["status"],
                previous_severity=previous["severity"],
                new_severity=incident["severity"],
                actor_type="system",
                actor_id=SYSTEM_ACTOR,
                reason="Authoritative evidence changed." if fingerprint_changed else "Severity changed.",
                evidence=candidate.evidence,
                correlation_id=correlation_id,
            ),
        )
        return TransitionSummary(candidate.candidate_key, action, incident["incident_id"], event_type.value)

    def _apply_healthy(
        self,
        connection: Any,
        incident: dict[str, Any],
        candidate: IncidentCandidate,
        now_text: str,
        correlation_id: str,
    ) -> TransitionSummary:
        previous = dict(incident)
        required = _healthy_count_for_rule(self.rule_config, candidate.rule_id)
        healthy_count = int(incident.get("healthy_observation_count", 0))
        if incident.get("evidence_fingerprint") != candidate.evidence_fingerprint:
            healthy_count += 1
        if not incident.get("healthy_since"):
            incident["healthy_since"] = candidate.observed_at
        incident.update(
            {
                "last_evaluated_at": now_text,
                "latest_evidence": candidate.evidence,
                "evidence_fingerprint": candidate.evidence_fingerprint,
                "healthy_observation_count": healthy_count,
                "updated_at": now_text,
            }
        )
        if incident["status"] != IncidentStatus.MONITORING.value and healthy_count < required:
            incident["status"] = IncidentStatus.MONITORING.value
            event_type = EventType.MONITORING_STARTED
            action = "updated"
        elif healthy_count >= required:
            incident.update({"status": IncidentStatus.RESOLVED.value, "resolved_at": now_text, "resolved_by": SYSTEM_ACTOR})
            event_type = EventType.AUTO_RESOLVED
            action = "resolved"
        else:
            event_type = None
            action = "skipped"
        self.repository.upsert_incident(connection, _normalize_incident_payload(incident))
        if event_type:
            self.repository.append_event(
                connection,
                _make_event(
                    incident=incident,
                    event_type=event_type,
                    now=now_text,
                    previous_status=previous["status"],
                    new_status=incident["status"],
                    previous_severity=previous["severity"],
                    new_severity=incident["severity"],
                    actor_type="system",
                    actor_id=SYSTEM_ACTOR,
                    reason="Healthy authoritative evidence observed.",
                    evidence=candidate.evidence,
                    correlation_id=correlation_id,
                ),
            )
        return TransitionSummary(candidate.candidate_key, action, incident["incident_id"], event_type.value if event_type else None)


def _normalize_incident_payload(incident: dict[str, Any]) -> dict[str, Any]:
    evidence = incident.get("latest_evidence", incident.get("evidence", {}))
    now = incident.get("updated_at") or utc_now()
    payload = {
        "incident_id": incident.get("incident_id") or incident_id_for(str(incident["deduplication_key"])),
        "deduplication_key": incident["deduplication_key"],
        "rule_id": incident["rule_id"],
        "rule_version": incident["rule_version"],
        "incident_type": incident.get("incident_type") or incident["rule_id"],
        "source": incident["source"],
        "feed_type": incident.get("feed_type"),
        "entity_type": incident["entity_type"],
        "entity_id": incident.get("entity_id"),
        "service_date": incident.get("service_date"),
        "operational_period_start": incident.get("operational_period_start") or incident.get("period_start"),
        "operational_period_end": incident.get("operational_period_end") or incident.get("period_end"),
        "status": incident.get("status", "OPEN"),
        "severity": incident.get("severity", "WARNING"),
        "title": incident.get("title", incident.get("rule_id", "Incident")),
        "summary": incident.get("summary", ""),
        "opened_at": incident.get("opened_at") or now,
        "first_observed_at": incident.get("first_observed_at") or incident.get("last_observed_at") or now,
        "last_observed_at": incident.get("last_observed_at") or now,
        "last_evaluated_at": incident.get("last_evaluated_at") or now,
        "healthy_since": incident.get("healthy_since"),
        "healthy_observation_count": int(incident.get("healthy_observation_count", 0)),
        "acknowledged_at": incident.get("acknowledged_at"),
        "acknowledged_by": incident.get("acknowledged_by"),
        "resolved_at": incident.get("resolved_at"),
        "resolved_by": incident.get("resolved_by"),
        "suppressed_at": incident.get("suppressed_at"),
        "suppressed_by": incident.get("suppressed_by"),
        "suppression_expires_at": incident.get("suppression_expires_at") or incident.get("suppressed_until"),
        "manual_resolution": 1 if incident.get("manual_resolution") else 0,
        "manual_resolution_note": incident.get("manual_resolution_note"),
        "occurrence_count": int(incident.get("occurrence_count", incident.get("observation_count", 1))),
        "recurrence_count": int(incident.get("recurrence_count", 0)),
        "evidence_version": int(incident.get("evidence_version", 1)),
        "latest_evidence": _safe_json(evidence),
        "evidence_fingerprint": incident.get("evidence_fingerprint") or _json_hash(evidence),
        "calculation_version": incident.get("calculation_version"),
        "serving_run_id": incident.get("serving_run_id"),
        "correlation_id": incident.get("correlation_id"),
        "created_at": incident.get("created_at") or now,
        "updated_at": now,
    }
    return payload


def _incident_from_candidate(candidate: IncidentCandidate, now_text: str, correlation_id: str) -> dict[str, Any]:
    severity = (candidate.suggested_severity or Severity.WARNING).value
    title = _title_for_candidate(candidate, severity)
    return {
        "incident_id": incident_id_for(candidate.candidate_key),
        "deduplication_key": candidate.candidate_key,
        "rule_id": candidate.rule_id,
        "rule_version": candidate.rule_version,
        "incident_type": candidate.rule_id.upper(),
        "source": candidate.source,
        "feed_type": candidate.feed_type,
        "entity_type": candidate.entity_type,
        "entity_id": candidate.entity_id,
        "service_date": candidate.service_date,
        "operational_period_start": candidate.period_start,
        "operational_period_end": candidate.period_end,
        "status": IncidentStatus.OPEN.value,
        "severity": severity,
        "title": title,
        "summary": title,
        "opened_at": now_text,
        "first_observed_at": candidate.observed_at,
        "last_observed_at": candidate.observed_at,
        "last_evaluated_at": now_text,
        "healthy_since": None,
        "healthy_observation_count": 0,
        "acknowledged_at": None,
        "acknowledged_by": None,
        "resolved_at": None,
        "resolved_by": None,
        "suppressed_at": None,
        "suppressed_by": None,
        "suppression_expires_at": None,
        "manual_resolution": 0,
        "manual_resolution_note": None,
        "occurrence_count": 1,
        "recurrence_count": 0,
        "evidence_version": 1,
        "latest_evidence": _safe_json(candidate.evidence),
        "evidence_fingerprint": candidate.evidence_fingerprint,
        "calculation_version": candidate.calculation_version,
        "serving_run_id": candidate.serving_run_id,
        "correlation_id": correlation_id,
        "created_at": now_text,
        "updated_at": now_text,
    }


def _make_event(
    *,
    incident: dict[str, Any],
    event_type: EventType,
    now: str,
    previous_status: str | None,
    new_status: str | None,
    actor_type: str,
    actor_id: str,
    reason: str | None,
    evidence: dict[str, Any] | None,
    correlation_id: str | None,
    previous_severity: str | None = None,
    new_severity: str | None = None,
) -> dict[str, Any]:
    fingerprint = _json_hash({"type": event_type.value, "incident_id": incident["incident_id"], "evidence": evidence, "reason": reason})
    return {
        "event_id": event_id_for(incident["incident_id"], event_type.value, fingerprint, now),
        "incident_id": incident["incident_id"],
        "event_type": event_type.value,
        "previous_status": previous_status,
        "new_status": new_status,
        "previous_severity": previous_severity,
        "new_severity": new_severity,
        "actor_type": actor_type,
        "actor_id": actor_id,
        "reason": reason,
        "evidence": _safe_json(evidence or {}),
        "rule_id": incident.get("rule_id"),
        "rule_version": incident.get("rule_version"),
        "correlation_id": correlation_id,
        "created_at": now,
    }


def _title_for_candidate(candidate: IncidentCandidate, severity: str) -> str:
    if candidate.rule_id == "stale_feed":
        return f"{severity}: {candidate.source} {candidate.feed_type} feed is stale"
    if candidate.rule_id == "low_realtime_coverage":
        return f"{severity}: {candidate.source} realtime coverage is low for {candidate.entity_type} {candidate.entity_id}"
    if candidate.rule_id == "severe_service_gap":
        return f"{severity}: severe service gap on route {candidate.entity_id}"
    if candidate.rule_id == "blocking_quality_failure":
        return f"CRITICAL: blocking quality validation failed for {candidate.source}"
    if candidate.rule_id == "stale_serving_artifact":
        return f"{severity}: {candidate.source} serving artifact is stale"
    return f"{severity}: {candidate.rule_id}"


def _healthy_count_for_rule(config: IncidentRuleConfig, rule_id: str) -> int:
    mapping = {
        "stale_feed": config.stale_feed,
        "low_realtime_coverage": config.low_realtime_coverage,
        "severe_service_gap": config.severe_service_gap,
        "blocking_quality_failure": config.blocking_quality_failure,
        "stale_serving_artifact": config.stale_serving_artifact,
    }
    return mapping[rule_id].healthy_observations_to_resolve


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate(
    *,
    key: str,
    rule_id: str,
    rule_version: str,
    source: str,
    state: CandidateState,
    observed_at: datetime,
    severity: Severity | None = None,
    feed_type: str | None = None,
    entity_type: str = "source",
    entity_id: str = "source",
    service_date: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    metric_name: str = "status",
    metric_value: float | None = None,
    warning_threshold: float | None = None,
    critical_threshold: float | None = None,
    healthy_threshold: float | None = None,
    confidence: str | None = None,
    coverage: float | None = None,
    calculation_version: str | None = None,
    serving_run_id: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> IncidentCandidate:
    return IncidentCandidate(
        candidate_key=key,
        rule_id=rule_id,
        rule_version=rule_version,
        source=source,
        feed_type=feed_type,
        entity_type=entity_type,
        entity_id=entity_id,
        service_date=service_date,
        period_start=period_start,
        period_end=period_end,
        observed_at=_ensure_utc(observed_at).isoformat(),
        metric_name=metric_name,
        metric_value=metric_value,
        warning_threshold=warning_threshold,
        critical_threshold=critical_threshold,
        healthy_threshold=healthy_threshold,
        candidate_state=state,
        suggested_severity=severity,
        confidence=confidence,
        coverage=coverage,
        calculation_version=calculation_version,
        serving_run_id=serving_run_id,
        evidence=evidence or {},
    )


def _stale_feed_candidates(
    source_id: str,
    source_cfg: dict[str, Any],
    rule: RuleSettings,
    history_root: Path,
    evaluation_time: datetime,
    correlation_id: str,
) -> list[IncidentCandidate]:
    candidates: list[IncidentCandidate] = []
    for feed_type in ("trip_updates", "vehicle_positions", "service_alerts"):
        feed_cfg = source_cfg.get("realtime", {}).get(feed_type, {})
        enabled = bool(feed_cfg.get("enabled"))
        key = f"stale_feed:{source_id}:{feed_type}"
        evidence: dict[str, Any] = {"source": source_id, "feed_type": feed_type, "capability_enabled": enabled, "correlation_id": correlation_id}
        if not rule.enabled or not enabled:
            candidates.append(
                _candidate(
                    key=key,
                    rule_id="stale_feed",
                    rule_version=rule.version,
                    source=source_id,
                    feed_type=feed_type,
                    state=CandidateState.NOT_APPLICABLE,
                    observed_at=evaluation_time,
                    entity_type="feed",
                    entity_id=feed_type,
                    evidence=evidence,
                )
            )
            continue
        snapshots = discover_committed_snapshots(history_root / source_id / feed_type)
        warning = rule.warning_after_seconds.get(feed_type, 300)
        critical = rule.critical_after_seconds.get(feed_type, warning * 3)
        evidence.update({"configured_warning_seconds": warning, "configured_critical_seconds": critical})
        if not snapshots:
            state = CandidateState.UNHEALTHY if rule.startup_grace_seconds <= 0 else CandidateState.UNKNOWN
            severity = Severity.CRITICAL if state == CandidateState.UNHEALTHY else None
            evidence.update(
                {
                    "latest_collection_time": None,
                    "feed_header_timestamp": None,
                    "feed_age_seconds": None,
                    "collection_lag_seconds": None,
                    "last_committed_snapshot_id": None,
                }
            )
            candidates.append(
                _candidate(
                    key=key,
                    rule_id="stale_feed",
                    rule_version=rule.version,
                    source=source_id,
                    feed_type=feed_type,
                    state=state,
                    severity=severity,
                    observed_at=evaluation_time,
                    entity_type="feed",
                    entity_id=feed_type,
                    metric_name="feed_age_seconds",
                    warning_threshold=warning,
                    critical_threshold=critical,
                    healthy_threshold=warning,
                    evidence=evidence,
                )
            )
            continue
        latest = snapshots[-1]
        collection_time = _parse_datetime(latest.get("collection_time"))
        feed_age = _float_or_none(latest.get("feed_age_seconds"))
        collection_lag = (evaluation_time - collection_time).total_seconds() if collection_time else None
        effective_age = max(feed_age or 0.0, collection_lag or 0.0)
        state = CandidateState.HEALTHY
        severity = None
        if effective_age >= critical:
            state, severity = CandidateState.UNHEALTHY, Severity.CRITICAL
        elif effective_age >= warning:
            state, severity = CandidateState.UNHEALTHY, Severity.WARNING
        evidence.update(
            {
                "latest_collection_time": collection_time.isoformat() if collection_time else latest.get("collection_time"),
                "feed_header_timestamp": latest.get("feed_header_timestamp"),
                "feed_age_seconds": effective_age,
                "collection_lag_seconds": collection_lag,
                "last_committed_snapshot_id": latest.get("snapshot_id"),
            }
        )
        candidates.append(
            _candidate(
                key=key,
                rule_id="stale_feed",
                rule_version=rule.version,
                source=source_id,
                feed_type=feed_type,
                state=state,
                severity=severity,
                observed_at=evaluation_time,
                entity_type="feed",
                entity_id=feed_type,
                metric_name="feed_age_seconds",
                metric_value=effective_age,
                warning_threshold=warning,
                critical_threshold=critical,
                healthy_threshold=warning,
                evidence=evidence,
            )
        )
    return candidates


def _serving_artifact_candidates(
    source_id: str,
    rule: RuleSettings,
    serving_root: Path,
    evaluation_time: datetime,
    correlation_id: str,
) -> list[IncidentCandidate]:
    key = f"stale_serving:{source_id}"
    warning = rule.warning_after_seconds.get("artifact", 1200)
    critical = rule.critical_after_seconds.get("artifact", 3600)
    evidence: dict[str, Any] = {
        "source": source_id,
        "configured_warning_seconds": warning,
        "configured_critical_seconds": critical,
        "correlation_id": correlation_id,
    }
    if not rule.enabled:
        return [
            _candidate(
                key=key,
                rule_id="stale_serving_artifact",
                rule_version=rule.version,
                source=source_id,
                state=CandidateState.NOT_APPLICABLE,
                observed_at=evaluation_time,
                entity_type="serving_artifact",
                entity_id="current",
                evidence=evidence,
            )
        ]
    try:
        pointer = read_current_pointer(source_id, serving_root)
        generated_at = _parse_datetime(pointer.get("generated_timestamp"))
        artifact_age = (evaluation_time - generated_at).total_seconds() if generated_at else None
        evidence.update(
            {
                "serving_run_id": pointer.get("serving_run_id"),
                "generated_at": generated_at.isoformat() if generated_at else pointer.get("generated_timestamp"),
                "artifact_age_seconds": artifact_age,
                "dbt_gold_run_id": pointer.get("dbt_gold_run_id"),
                "latest_realtime_watermark": pointer.get("latest_included_realtime_snapshot"),
                "quality_status": pointer.get("quality_status"),
                "readiness_status": "ready",
            }
        )
        state = CandidateState.HEALTHY
        severity = None
        if artifact_age is None:
            state, severity = CandidateState.UNKNOWN, None
        elif artifact_age >= critical:
            state, severity = CandidateState.UNHEALTHY, Severity.CRITICAL
        elif artifact_age >= warning:
            state, severity = CandidateState.UNHEALTHY, Severity.WARNING
        return [
            _candidate(
                key=key,
                rule_id="stale_serving_artifact",
                rule_version=rule.version,
                source=source_id,
                state=state,
                severity=severity,
                observed_at=evaluation_time,
                entity_type="serving_artifact",
                entity_id="current",
                metric_name="artifact_age_seconds",
                metric_value=artifact_age,
                warning_threshold=warning,
                critical_threshold=critical,
                healthy_threshold=warning,
                serving_run_id=pointer.get("serving_run_id"),
                evidence=evidence,
            )
        ]
    except Exception as exc:
        evidence.update(
            {
                "serving_run_id": None,
                "generated_at": None,
                "artifact_age_seconds": None,
                "dbt_gold_run_id": None,
                "latest_realtime_watermark": None,
                "quality_status": "unknown",
                "readiness_status": "unavailable",
                "reason": exc.__class__.__name__,
            }
        )
        return [
            _candidate(
                key=key,
                rule_id="stale_serving_artifact",
                rule_version=rule.version,
                source=source_id,
                state=CandidateState.UNHEALTHY,
                severity=Severity.CRITICAL,
                observed_at=evaluation_time,
                entity_type="serving_artifact",
                entity_id="current",
                metric_name="artifact_age_seconds",
                warning_threshold=warning,
                critical_threshold=critical,
                healthy_threshold=warning,
                evidence=evidence,
            )
        ]


def _quality_candidates(source_id: str, rule: RuleSettings, quality_root: Path, evaluation_time: datetime, correlation_id: str) -> list[IncidentCandidate]:
    key = f"quality_failure:{source_id}:all"
    evidence: dict[str, Any] = {"source": source_id, "artifact_type": "all", "correlation_id": correlation_id}
    if not rule.enabled:
        return [
            _candidate(
                key=key,
                rule_id="blocking_quality_failure",
                rule_version=rule.version,
                source=source_id,
                state=CandidateState.NOT_APPLICABLE,
                observed_at=evaluation_time,
                entity_type="quality_artifact",
                entity_id="all",
                evidence=evidence,
            )
        ]
    path = quality_root / "latest_validation_summary.json"
    if not path.is_file():
        evidence.update(
            {
                "quality_run_id": None,
                "artifact_run_id": None,
                "suite": "all",
                "expectations_evaluated": 0,
                "expectations_failed": None,
                "blocking_failures": None,
                "failed_expectation_names": [],
                "generated_at": None,
                "reason": "summary_unavailable",
            }
        )
        return [
            _candidate(
                key=key,
                rule_id="blocking_quality_failure",
                rule_version=rule.version,
                source=source_id,
                state=CandidateState.UNHEALTHY,
                severity=Severity.CRITICAL,
                observed_at=evaluation_time,
                entity_type="quality_artifact",
                entity_id="all",
                metric_name="blocking_failures",
                evidence=evidence,
            )
        ]
    payload = json.loads(path.read_text(encoding="utf-8"))
    failed = payload.get("failed_expectations", [])
    failed_names = [str(item.get("expectation_type", item)) for item in failed[:25]] if isinstance(failed, list) else []
    failed_count = int(payload.get("expectations_failed", len(failed) if isinstance(failed, list) else failed or 0) or 0)
    success = bool(payload.get("success", False))
    evidence.update(
        {
            "quality_run_id": payload.get("quality_run_id") or payload.get("run_id") or payload.get("generated_timestamp"),
            "artifact_run_id": payload.get("artifact_run_id"),
            "suite": payload.get("suite", "all"),
            "expectations_evaluated": int(payload.get("expectations_evaluated", 0) or 0),
            "expectations_failed": failed_count,
            "blocking_failures": failed_count,
            "failed_expectation_names": failed_names,
            "generated_at": payload.get("generated_timestamp"),
        }
    )
    return [
        _candidate(
            key=key,
            rule_id="blocking_quality_failure",
            rule_version=rule.version,
            source=source_id,
            state=CandidateState.HEALTHY if success else CandidateState.UNHEALTHY,
            severity=None if success else Severity.CRITICAL,
            observed_at=evaluation_time,
            entity_type="quality_artifact",
            entity_id="all",
            metric_name="blocking_failures",
            metric_value=float(failed_count),
            critical_threshold=1.0,
            healthy_threshold=0.0,
            evidence=evidence,
        )
    ]


def _coverage_candidates(db_path: Path, pointer: dict[str, Any], rule: RuleSettings, evaluation_time: datetime, correlation_id: str) -> list[IncidentCandidate]:
    if not rule.enabled:
        return []
    serving_run_id = str(pointer.get("serving_run_id") or "")
    candidates: list[IncidentCandidate] = []
    with duckdb.connect(str(db_path), read_only=True) as connection:
        rows = connection.execute("SELECT * FROM v_realtime_trip_coverage").fetchall()
        columns = [desc[0] for desc in connection.description]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for values in rows:
        row = dict(zip(columns, values, strict=True))
        grouped.setdefault((str(row["source"]), str(row["service_date"]), str(row["service_period"])), []).append(row)
        candidates.append(_coverage_candidate_from_row(row, rule, evaluation_time, serving_run_id, correlation_id, scope="route"))
    for (source, service_date, service_period), route_rows in grouped.items():
        eligible = sum(int(row.get("eligible_scheduled_trip_count") or 0) for row in route_rows)
        observed = sum(int(row.get("observed_eligible_trip_count") or 0) for row in route_rows)
        coverage = round(100.0 * observed / eligible, 2) if eligible else None
        row = {
            "source": source,
            "service_date": service_date,
            "route_id": "network",
            "service_period": service_period,
            "feed_type": "trip_updates",
            "calculation_version": route_rows[0].get("calculation_version"),
            "eligible_scheduled_trip_count": eligible,
            "observed_eligible_trip_count": observed,
            "unobserved_eligible_trip_count": max(0, eligible - observed),
            "unmatched_realtime_trip_count": sum(int(row.get("unmatched_realtime_trip_count") or 0) for row in route_rows),
            "coverage_percentage": coverage,
            "coverage_status": "OBSERVED" if observed else "NO_REALTIME_EVIDENCE",
            "confidence_status": "HIGH" if coverage is not None and coverage >= 80 else "NO_COVERAGE",
        }
        candidates.append(_coverage_candidate_from_row(row, rule, evaluation_time, serving_run_id, correlation_id, scope="network"))
    return candidates


def _coverage_candidate_from_row(
    row: dict[str, Any],
    rule: RuleSettings,
    evaluation_time: datetime,
    serving_run_id: str,
    correlation_id: str,
    *,
    scope: str,
) -> IncidentCandidate:
    source = str(row["source"])
    service_date = str(row["service_date"])
    service_period = str(row["service_period"])
    route_id = str(row["route_id"])
    eligible = int(row.get("eligible_scheduled_trip_count") or 0)
    coverage = _float_or_none(row.get("coverage_percentage"))
    confidence = str(row.get("confidence_status") or "")
    entity_id = "network" if scope == "network" else route_id
    key = (
        f"low_coverage:{source}:{scope}:{service_date}:{service_period}"
        if scope == "network"
        else f"low_coverage:{source}:route:{route_id}:{service_date}:{service_period}"
    )
    evidence = {
        "eligible_scheduled_trip_count": eligible,
        "observed_eligible_trip_count": int(row.get("observed_eligible_trip_count") or 0),
        "unobserved_eligible_trip_count": int(row.get("unobserved_eligible_trip_count") or 0),
        "unmatched_realtime_trip_count": int(row.get("unmatched_realtime_trip_count") or 0),
        "coverage_percentage": coverage,
        "coverage_status": row.get("coverage_status"),
        "confidence_status": confidence,
        "service_period": service_period,
        "calculation_version": row.get("calculation_version"),
        "serving_run_id": serving_run_id,
        "correlation_id": correlation_id,
    }
    if eligible < rule.minimum_eligible_trips:
        state, severity = CandidateState.NOT_ENOUGH_DATA, None
    elif coverage is None:
        state, severity = CandidateState.UNKNOWN, None
    elif coverage >= rule.healthy_at_or_above_percentage and confidence in rule.confidence_statuses:
        state, severity = CandidateState.HEALTHY, None
    elif coverage < rule.critical_below_percentage:
        state, severity = CandidateState.UNHEALTHY, Severity.CRITICAL
    elif coverage < rule.warning_below_percentage:
        state, severity = CandidateState.UNHEALTHY, Severity.WARNING
    else:
        state, severity = CandidateState.UNKNOWN, None
    return _candidate(
        key=key,
        rule_id="low_realtime_coverage",
        rule_version=rule.version,
        source=source,
        feed_type="trip_updates",
        entity_type=scope,
        entity_id=entity_id,
        service_date=service_date,
        period_start=f"{service_date}T00:00:00+00:00",
        period_end=f"{service_date}T23:59:59+00:00",
        observed_at=evaluation_time,
        metric_name="coverage_percentage",
        metric_value=coverage,
        warning_threshold=rule.warning_below_percentage,
        critical_threshold=rule.critical_below_percentage,
        healthy_threshold=rule.healthy_at_or_above_percentage,
        state=state,
        severity=severity,
        confidence=confidence,
        coverage=coverage,
        calculation_version=row.get("calculation_version"),
        serving_run_id=serving_run_id,
        evidence=evidence,
    )


def _service_gap_candidates(
    db_path: Path, pointer: dict[str, Any], rule: RuleSettings, evaluation_time: datetime, correlation_id: str
) -> list[IncidentCandidate]:
    if not rule.enabled:
        return []
    serving_run_id = str(pointer.get("serving_run_id") or "")
    with duckdb.connect(str(db_path), read_only=True) as connection:
        try:
            rows = connection.execute("SELECT * FROM v_headway_reliability_events").fetchall()
            columns = [desc[0] for desc in connection.description]
        except duckdb.CatalogException:
            return []
    candidates = []
    for values in rows:
        row = dict(zip(columns, values, strict=True))
        if row.get("event_type") != "SERVICE_GAP":
            continue
        source = str(row["source"])
        route_id = str(row["route_id"])
        direction_id = str(row.get("direction_id") or "unknown")
        stop_id = str(row.get("reference_stop_id") or "unknown")
        event_time = _parse_datetime(row.get("event_timestamp")) or evaluation_time
        window = event_time.strftime("%Y%m%dT%H%M")
        key = f"service_gap:{source}:{route_id}:{direction_id}:{stop_id}:{window}"
        ratio = _float_or_none(row.get("headway_ratio"))
        coverage = _float_or_none(row.get("coverage"))
        confidence = str(row.get("confidence") or row.get("observation_method") or "")
        state = CandidateState.UNHEALTHY if ratio is not None and ratio >= rule.critical_headway_ratio else CandidateState.UNKNOWN
        severity = Severity.CRITICAL if state == CandidateState.UNHEALTHY else None
        evidence = {
            "route_id": route_id,
            "direction_id": direction_id,
            "reference_stop_id": stop_id,
            "event_timestamp": event_time.isoformat(),
            "planned_headway_seconds": _float_or_none(row.get("planned_headway_seconds")),
            "observed_headway_seconds": _float_or_none(row.get("observed_headway_seconds")),
            "headway_ratio": ratio,
            "threshold_ratio": rule.critical_headway_ratio,
            "observation_method": row.get("observation_method"),
            "coverage": coverage,
            "confidence": confidence,
            "evidence_key": row.get("evidence_key"),
            "calculation_version": row.get("calculation_version"),
            "serving_run_id": serving_run_id,
            "correlation_id": correlation_id,
        }
        candidates.append(
            _candidate(
                key=key,
                rule_id="severe_service_gap",
                rule_version=rule.version,
                source=source,
                entity_type="route",
                entity_id=route_id,
                service_date=str(row.get("service_date")) if row.get("service_date") else None,
                period_start=event_time.replace(minute=0, second=0, microsecond=0).isoformat(),
                period_end=(event_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)).isoformat(),
                observed_at=evaluation_time,
                metric_name="headway_ratio",
                metric_value=ratio,
                critical_threshold=rule.critical_headway_ratio,
                healthy_threshold=rule.critical_headway_ratio,
                state=state,
                severity=severity,
                confidence=confidence,
                coverage=coverage,
                calculation_version=row.get("calculation_version"),
                serving_run_id=serving_run_id,
                evidence=evidence,
            )
        )
    return candidates


def migrate_incident_store(root: Path = DEFAULT_INCIDENT_ROOT) -> dict[str, Any]:
    repository = incident_repository(root)
    starting_version = 0
    with contextlib.suppress(Exception):
        starting_version = repository.schema_version()
    repository.migrate()
    ending_version = repository.schema_version()
    return {
        "backend": incident_backend(),
        "target": repository.target_label(),
        "starting_schema_version": starting_version,
        "ending_schema_version": ending_version,
        "applied_migrations": [] if starting_version == ending_version else [ending_version],
        "status": "ok",
    }


def evaluation_result_to_dict(result: EvaluationResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["transitions"] = [asdict(transition) for transition in result.transitions]
    return payload
