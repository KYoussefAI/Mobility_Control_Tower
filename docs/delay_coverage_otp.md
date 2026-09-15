# Delay, Coverage, And On-Time Performance

dbt owns the authoritative observation, coverage, delay-distribution, and OTP
models. Coverage compares matched realtime trip evidence with an explicit
eligible scheduled-trip denominator. Missing observations are unknown: they are
not treated as on-time and are not classified as cancellation.

Delay models prefer arrival delay when present, retain missing delay as null,
exclude stale or implausible values, and publish sample/coverage context. OTP uses
configurable project thresholds; it is not a universal transit standard or proof
of passenger experience.
