# GTFS-Realtime exploration

## What GTFS-Realtime is

GTFS-Realtime is the live companion to static GTFS. Static GTFS describes the planned offer. GTFS-Realtime describes operational information observed around fetch time.

Common GTFS-Realtime feed entity types are:

- Trip Updates: changes or predictions for trips and stop times.
- Vehicle Positions: vehicle location and status information.
- Service Alerts: disruptions, messages, and informed routes, stops, or trips.

## Tisseo context

The official transport.data.gouv.fr dataset page states that Tisseo publishes GTFS-RT data and lists a combined `GtfsRt.pb` resource containing TripUpdate and Alert entities, plus an `Alert.pb` resource containing alerts. Vehicle Positions are not listed as available there, so the project leaves the vehicle positions URL unset unless a reliable official endpoint is provided later.

## Why snapshots first

This phase fetches one protobuf file and saves it unchanged as `feed.pb`. That file is a deterministic local snapshot. It can be reused for:

- parser tests;
- replay experiments;
- demos without live internet;
- static/live compatibility checks.

This is intentionally not continuous streaming. There is no Kafka, Spark, Airflow, database, API, dashboard, or cloud service in this phase.

## Why static/live compatibility matters

Future real-time reliability indicators need joins between live observations and static schedule data. Before building those indicators, the project must answer whether live `route_id`, `trip_id`, and `stop_id` values can be matched to the silver static GTFS tables.

The compatibility report measures how many identifiers match and how many are unmatched. Perfect matching is not required during exploration, but the result shows whether the feed is a candidate for later real-time phases.

## What the real-time gold layer adds

The real-time gold layer combines one parsed Trip Updates snapshot with the static silver GTFS tables. It creates:

- feed health indicators;
- enriched trip update rows with static route and trip match flags;
- route delay snapshot indicators;
- stop delay snapshot indicators;
- identifier compatibility percentages;
- static PNG charts and a teacher-facing Markdown report.

These are snapshot indicators observed at fetch time, not continuous real-time reliability metrics.

## Why trip ID mismatch can happen

Trip IDs can fail to match when the selected static GTFS run does not exactly correspond to the real-time publication, when operational trips are represented differently in real-time, or when the real-time feed exposes partial or modified trip descriptors. This is why the project keeps unmatched trip rows instead of dropping them.

## Why route IDs and stop IDs still matter

Route and stop identifiers are often more stable than trip identifiers. If `route_id` and `stop_id` compatibility are strong, the snapshot can still support route-level and stop-level exploration while trip-level joins remain under review.

## Why this does not justify Kafka or Spark yet

One snapshot proves parsing and compatibility, not sustained volume, velocity, or production operations. Before introducing streaming tools, the project should collect multiple snapshots, compare freshness, inspect identifier stability, and confirm that delay indicators remain interpretable.

## What results are needed before streaming later

Before any streaming phase, the project should have evidence that:

- a GTFS-Realtime snapshot can be fetched and preserved;
- the protobuf can be parsed into simple tables;
- feed age can be estimated from the header timestamp;
- useful identifiers are present;
- identifiers mostly match static silver GTFS;
- saved snapshots can reproduce the same parser and compatibility outputs offline.
