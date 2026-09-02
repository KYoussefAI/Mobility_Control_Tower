# Mobility Control Tower

## Overview

The validated static GTFS pipeline produces schedule-based transport indicators and reports. Python derives network and route activity from canonical Silver tables and renders local analytical outputs without an external service.

## Data Flow

```text
GTFS -> Raw -> Bronze -> Silver -> quality validation -> Python Gold metrics and reports
```

The analytical layer uses scheduled service, not observed vehicle movement. Its results describe planned activity and must not be interpreted as measured operational performance.

## Running the Project

```bash
python -m pip install -e '.[quality,analytics]'
mobility-control-tower build-gold
```

See [`docs/data_quality.md`](docs/data_quality.md) and [`docs/data_source.md`](docs/data_source.md) for validation and provenance.

## Limitations

Gold construction is implemented in Python here. There is no dbt project, serving database, API, dashboard, or GTFS-Realtime ingestion.
