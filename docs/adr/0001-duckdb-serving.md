# ADR 0001: DuckDB Serving

Decision: keep DuckDB as the local analytical serving artifact.

Reasoning: the project is local-first and favors deterministic embedded analytical serving. A server warehouse would add operational complexity without improving reproducibility or reviewability. dbt remains the owner of Gold transformations; DuckDB serves the atomic published artifact.

Consequence: the API must never expose arbitrary SQL, and serving publication must remain atomic through `current.json`.
