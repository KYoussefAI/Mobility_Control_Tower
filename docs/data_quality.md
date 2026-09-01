# Silver data quality

The Silver validator checks required GTFS tables and columns, key uniqueness,
coordinates, route types, time syntax, and references between stops, routes,
trips, stop times, and service calendars.

- **PASS** means no problem was detected.
- **WARN** marks a usable but unusual value that deserves review.
- **FAIL** marks a missing requirement or broken relationship.

Validation reports findings without mutating the canonical Silver tables.
