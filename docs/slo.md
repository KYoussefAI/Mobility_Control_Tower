# Service-Level Objectives

These are project targets for the local operational prototype. Historical compliance is not claimed until the metrics have been collected over the stated windows.

| SLO | Indicator | Target | Window | Alert threshold | Source |
| --- | --- | --- | --- | --- | --- |
| Static pipeline success | latest daily static workflow status | 99% successful runs | 30 days | latest static pipeline failed | pipeline manifests / exporter |
| Realtime collection success | committed snapshots / attempted snapshots | 95% | 24 hours | no collection for configured period | snapshot manifests |
| Trip Update freshness | feed age seconds | warning under 90s | 15 minutes | warning 90s, critical 300s | feed summary |
| Vehicle Position freshness | feed age seconds | warning under 90s when feed exists | 15 minutes | warning 90s, critical 300s | feed summary |
| Service Alert freshness | feed age seconds | warning under 600s when feed exists | 1 hour | warning 600s, critical 1800s | feed summary |
| Incremental analytical delay | watermark age seconds | under refresh interval plus lookback | 1 hour | watermark too old | watermark state |
| Serving readiness | API readiness status | 99% ready | 24 hours | readiness failing | API and serving manifest |
| API p95 latency | request duration p95 | under documented local threshold | 1 hour | elevated p95 | API metrics |
| Quality contracts | latest validation status | 100% success for publication | every publication | quality failed | MCT Quality Contracts |

Exclusions: planned local maintenance, unsupported source capabilities, deterministic demo reset, and unavailable live feeds in fixture mode.
