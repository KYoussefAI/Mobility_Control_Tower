# Tisséo data source

The selected dataset is **Tisséo — Réseau transport urbain toulousain**. Tisséo Voyageurs produces transport data for the Toulouse urban network. The static GTFS describes the theoretical public-transport offer: stops, schedules, and lines. It is published daily and covers approximately the next three weeks.

Official pages:

- [French National Access Point for transport data](https://transport.data.gouv.fr/datasets/tisseo-reseau-transport-urbain-toulousain)
- [data.gouv.fr dataset page](https://www.data.gouv.fr/datasets/tisseo-reseau-transport-urbain-toulousain)

The dataset page identifies the licence as the **Open Data Commons Open Database License (ODbL)**. This project records that licence identifier in ingestion metadata; it does not reinterpret or add licence terms.

## Why start with static GTFS?

Static GTFS is finite, file-based, reproducible, and easy to inspect. It gives this first phase a clear foundation for raw-data preservation, metadata, and data-quality profiling before any continuously changing inputs are introduced.

Tisséo also publishes GTFS-RT real-time data. It is postponed because real-time ingestion introduces polling, changing state, and operational concerns that are outside this phase. No GTFS-RT data is downloaded or processed here.
