# Immutable GTFS-Realtime Acquisition

The acquisition layer makes one bounded HTTP request and preserves the original
protobuf bytes in a new run directory. Metadata records source, feed type, URL,
UTC fetch time, HTTP status, content type, byte count, and SHA-256.

Responses are size-bounded, redirects are rejected, and configured source hosts
form an allow-list. An empty response, unexpected content type, HTTP error, or
directory collision fails without representing the fetch as successful.

This layer does not parse the protobuf or calculate service indicators. Saving a
snapshot proves only what bytes were acquired at that time.
