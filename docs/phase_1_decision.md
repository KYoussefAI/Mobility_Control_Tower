# Phase 1 decision

The first implementation slice uses only Tisséo static GTFS. Each source archive is copied unchanged into a timestamped raw run, accompanied by provenance metadata and a SHA256 checksum. Profiling reads directly from that preserved ZIP and writes human- and machine-readable reports.

This deliberately establishes reproducibility and basic observability before adding transformations or infrastructure. Generated data is ignored by Git.
