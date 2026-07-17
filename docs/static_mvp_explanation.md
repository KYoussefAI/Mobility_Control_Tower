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

This phase does not prove real-time reliability. It does not process GTFS-RT, delays, cancellations, vehicle positions, passenger counts, or observed waiting time.

The KPIs are scheduled-service indicators:

- scheduled trips, not actual trips;
- scheduled departures, not observed departures;
- planned headway approximation, not real passenger waiting time.

## Why this is a valid first Data Engineering slice

A Data Engineering project should first make source data trustworthy and usable. This slice covers ingestion, raw preservation, metadata, layered transformation, validation, manifests, tests, and analytical outputs.

That foundation is useful before adding real-time data because future reliability indicators need a clean static schedule baseline.

## What real-time data will add later

Real-time data can later compare observed service against the planned schedule. It could add actual arrival times, delays, missed trips, vehicle positions, headway regularity, and planned-versus-observed reliability indicators.

Those features are intentionally postponed so the static pipeline remains simple, testable, and explainable.
