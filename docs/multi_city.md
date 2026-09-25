# Multi-city configuration and storage

The source catalogue is city-aware without changing the local-first architecture. `config/sources.yml` contains independent Toulouse and Rennes definitions, including static and realtime endpoints, licence metadata, time zones, and expected feed freshness.

Select a source with `MCT_GTFS_SOURCE`; typed settings reject unsupported operational combinations. The default storage backend remains the local filesystem. `StorageBackend` also defines an optional S3 implementation through boto3, so collection code can depend on one bounded interface without claiming a cloud deployment.

This implementation demonstrates configuration and storage portability only. It does not claim multi-tenant isolation, distributed processing, high availability, or cloud-scale operations.
