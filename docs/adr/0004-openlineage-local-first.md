# ADR 0004: OpenLineage Local-First

Decision: emit OpenLineage-compatible local JSONL events and expose honest lineage status before requiring a backend.

Reasoning: lineage must not block the deterministic demo. Stable dataset namespaces and event shapes are validated locally; the optional remote backend is not enabled by default.

Consequence: the API reports lineage as disabled unless explicitly enabled. Local events are evidence of event generation, not proof that Marquez or another backend is running.
