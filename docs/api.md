# Local read-only API

## Purpose

The API exposes the DuckDB serving database through simple JSON endpoints. It proves that the project can serve trusted data products to future consumers such as a dashboard, notebook, external application, or teacher demo.

This is a local read-only API. It does not modify data.

## Start the API

```bash
python -m mobility_control_tower.cli serve-api \
  --db data/serving/tisseo/<run_id>/mobility_control_tower.duckdb \
  --host 127.0.0.1 \
  --port 8000
```

Interactive FastAPI documentation is available at:

`http://127.0.0.1:8000/docs`

## Basic endpoints

### GET /health

Returns service status and whether the DuckDB database can be opened.

### GET /metadata

Returns the database path, available tables, available views, and whether static and real-time snapshot data are present.

## Static planning endpoints

### GET /static/network-overview

Reads `v_network_overview`.

Query parameters:

- `limit`: default 20, max 100.

### GET /static/top-routes

Reads `v_top_routes_static`.

Query parameters:

- `limit`: default 10, max 100.

### GET /static/hourly-headway

Reads `v_route_hourly_headway`.

Query parameters:

- `route_id`: optional.
- `service_date`: optional.
- `limit`: default 50, max 500.

Example:

`/static/hourly-headway?route_id=line:69&service_date=2026-07-31&limit=10`

### GET /static/route-types

Reads `v_route_type_daily_summary`.

Query parameters:

- `service_date`: optional.
- `limit`: default 50, max 500.

## Real-time snapshot endpoints

These endpoints work only when the DuckDB file contains real-time snapshot views. If not, they return HTTP 404 with a clear message.

### GET /realtime/feed-health

Reads `v_rt_feed_health`.

### GET /realtime/compatibility

Reads `v_rt_identifier_compatibility`.

### GET /realtime/top-delayed-routes

Reads `v_rt_top_delayed_routes_snapshot`.

Query parameters:

- `limit`: default 10, max 100.

### GET /realtime/top-delayed-stops

Reads `v_rt_top_delayed_stops_snapshot`.

Query parameters:

- `limit`: default 10, max 100.

## Response format

Most endpoints return:

```json
{
  "data": [],
  "count": 0,
  "source": "view_name",
  "notes": []
}
```

## Limitations

- This is not a production API.
- It has no authentication because it is local and read-only.
- It does not expose arbitrary SQL.
- It does not implement a dashboard.
- It does not implement continuous streaming.
- Real-time endpoints are snapshot-based.

## Why this prepares a future dashboard

A dashboard can later consume these endpoints instead of reading local CSV files directly. The API creates a clean contract between data products and future user interfaces.
