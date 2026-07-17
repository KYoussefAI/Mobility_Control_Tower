# Basic GTFS data quality

The silver validator checks whether core tables and columns exist, reports row counts, and detects:

- missing key values and duplicate stop, route, or trip identifiers;
- invalid stop latitude and longitude;
- uncommon or invalid obvious `route_type` values;
- invalid arrival and departure time syntax, including support for valid hours above 23;
- stop times referencing unknown trips or stops;
- trips referencing unknown routes or service identifiers.

## Status meanings

- **PASS**: the check found no problems.
- **WARN**: the data deserves review, but the condition may be an extension or a usable non-critical value. The route-type range check uses this status.
- **FAIL**: a required structure, value, format, uniqueness rule, or relationship has a detected problem.

The report's overall status is the most severe individual status. Validation reports findings without modifying silver data or stopping merely because a check fails.

## Limitations

This is educational, basic validation rather than complete GTFS certification. It does not implement the full GTFS Schedule specification, conditional field requirements, geographic plausibility within Toulouse, ordering rules, schedule consistency, shape validation, translated feeds, or every extended route type. It counts problems but does not include potentially sensitive or very large lists of affected rows. A dedicated standards validator would still be appropriate before production publication.
