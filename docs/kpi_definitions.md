# Static GTFS KPI definitions

These gold indicators describe the **planned transport offer** in Tisséo's static schedule.

## Scheduled trips by route and day

One row represents one route on one service date. `scheduled_trips_count` counts trips whose `service_id` is active that day. This is the main first-version KPI because it makes planned route supply easy to compare across dates.

## Scheduled departures by route and hour

One row represents one route, service date, and service-day hour. Only the minimum `stop_sequence` for each trip is counted, so the value represents trip starts rather than all station calls. GTFS hours after midnight remain 24, 25, and so on.

## Scheduled stop departures by day

One row represents one stop on one service date. Every stop-time departure with a usable departure time is counted, giving the planned activity at that stop.

## Network daily summary

One row represents a service date and reports active routes, scheduled trips, scheduled stop departures, and active stops. It is a compact overview of the scheduled network supply.

## Route period summary

One row represents one route over the full GTFS service period. It reports active service days, total scheduled trips, average trips per active day, maximum daily trips, and the first and last service dates. Use this table when saying "top routes over the GTFS service period".

## Planned hourly headway

One row represents one route, service date, and service-day hour. `planned_headway_minutes` is `60 / scheduled_departures_count`. This is an approximate planned headway from the static schedule, not real passenger waiting time.

## Route type daily summary

One row represents one service date and GTFS route type. It reports active routes, scheduled trips, and scheduled stop departures for labels such as Tram, Subway/Metro, Bus, and other standard GTFS route types. Unknown route types are labelled Unknown.

## Busiest route/day

This table keeps the top 50 individual route/day combinations by scheduled trips. It is useful for evidence because it avoids mixing a per-day peak with a full-period total.

## Busiest stop/day

This table keeps the top 50 individual stop/day combinations by scheduled departures. It identifies high-activity planned stop days, not observed passenger demand.

## Service calendars

Regular weekday service is expanded between `start_date` and `end_date`. A `calendar_dates` exception type 1 adds service; type 2 removes it. If only `calendar_dates` exists, additions define the available dates.

## Why these are not reliability KPIs

Static GTFS says what should run, not what actually happened. These KPIs measure planned supply and establish a comparison baseline. Future real-time observations could add actual arrivals, delays, cancellations, headway regularity, and planned-versus-observed reliability. Those concerns are intentionally outside the current phase.
