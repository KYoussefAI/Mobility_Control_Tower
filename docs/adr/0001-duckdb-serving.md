# ADR 0001: DuckDB Serving

Decision: keep DuckDB as the local analytical serving artifact.

Reasoning: the project is local-first. dbt remains the owner of Gold
transformations, while DuckDB publishes a bounded, atomic analytical artifact.

Consequence: serving publication validates required static views before exposing
the new database.
