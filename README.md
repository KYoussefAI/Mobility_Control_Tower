# Mobility Control Tower

## Overview

The static Tisséo pipeline couples Raw, Bronze, and Silver processing with explicit data-quality validation. Declarative expectations and a checkpoint assess curated Silver tables, while validation results remain separate from the data they evaluate.

## Architecture

```text
GTFS -> Raw -> Bronze -> Silver -> quality contract -> validation result
```

Python owns ingestion and layer construction. The quality component checks structural and domain assumptions after normalization, making the acceptance boundary visible rather than treating file creation as proof of usable data.

## Running and Verification

```bash
python -m pip install -e '.[quality]'
mobility-control-tower --help
```

The checked invariants are described in [`docs/data_quality.md`](docs/data_quality.md); source provenance is covered by [`docs/data_source.md`](docs/data_source.md). Tests exercise the static pipeline and validation behavior.

There are no Gold marts, serving database, API, or scheduler. Operation is local and manual.
