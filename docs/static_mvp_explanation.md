# Static MVP explanation

## What the static MVP proves

The static MVP proves that the project can take an official public-transport GTFS ZIP and turn it into reproducible Data Engineering outputs:

- immutable raw data preservation with metadata and checksum;
- bronze extraction of source GTFS files;
- cleaned silver tables;
- basic quality validation;
- gold static planning KPIs;
- Markdown reports and PNG charts that can be regenerated.

The important point is repeatability. The same workflow can be run again on a new daily Tisseo GTFS publication and produce comparable outputs.

## What it does not prove

The static pipeline does not prove real-time reliability. Its outputs do not represent GTFS-RT observations, delays, cancellations, vehicle positions, passenger counts, or observed waiting time.

The KPIs are scheduled-service indicators:

- scheduled trips, not actual trips;
- scheduled departures, not observed departures;
- planned headway approximation, not real passenger waiting time.

## Why this is a valid first Data Engineering slice

A Data Engineering project should first make source data trustworthy and usable. This slice covers ingestion, raw preservation, metadata, layered transformation, validation, manifests, tests, and analytical outputs.

The static schedule remains the reference used to interpret observed service data without conflating planned and observed behavior.

## Scope boundary

This module describes scheduled service only. Realtime and historical reliability calculations are separate data products with their own eligibility and quality rules.
