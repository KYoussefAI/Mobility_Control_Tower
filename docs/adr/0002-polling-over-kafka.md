# ADR 0002: Polling Over Kafka

Decision: use bounded polling and immutable snapshot commits rather than Kafka.

Reasoning: public GTFS-Realtime feeds are polled HTTP resources, the deterministic demo must run locally, and the required evidence can be captured with committed protobuf snapshots plus watermarks.

Consequence: the system is near-realtime, not a true streaming platform. Collection cadence and analytical refresh cadence stay decoupled.
