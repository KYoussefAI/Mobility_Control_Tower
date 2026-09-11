# Tisséo GTFS sources

The project uses the Tisséo Toulouse static GTFS schedule and the configured
GTFS-Realtime feeds for Trip Updates and Service Alerts. Vehicle Positions are
recorded as unavailable in the source capability configuration.

Static archives and realtime protobuf snapshots are preserved unchanged with
source, timestamp, checksum, and HTTP provenance metadata before parsing.
