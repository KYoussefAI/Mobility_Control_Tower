# ADR 0003: Incident Model

Decision: incidents are persistent state records with append-only audit events.

Reasoning: operators need acknowledgement, resolution, suppression, and evidence history. Repeated detections must update one incident through a deterministic deduplication key instead of creating one record per poll.

Consequence: incident mutations require scoped bearer tokens and audit events. The current local store can later move to PostgreSQL without changing the API contract.
