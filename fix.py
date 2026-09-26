from pathlib import Path

progress = Path("progress")

targets = [
    "dbt/models/intermediate/int_first_trip_departures.sql",
    "dbt/models/intermediate/int_service_dates.sql",
    "dbt/models/intermediate/int_trip_base.sql",
    "dbt/models/marts/busiest_route_day.sql",
    "dbt/models/marts/busiest_stop_day.sql",
    "dbt/models/marts/route_daily_trips.sql",
    "dbt/models/marts/route_hourly_departures.sql",
    "dbt/models/marts/route_hourly_headway.sql",
    "dbt/models/marts/route_period_summary.sql",
    "dbt/models/marts/stop_daily_departures.sql",
    "dbt/models/staging/stg_calendar.sql",
    "dbt/models/staging/stg_calendar_dates.sql",
    "dbt/models/staging/stg_routes.sql",
    "dbt/models/staging/stg_stop_times.sql",
    "dbt/models/staging/stg_stops.sql",
    "dbt/models/staging/stg_trips.sql",
    "quality_contracts/checkpoints/gold_checkpoint.yml",
    "quality_contracts/expectations/gold_suite.json",
]

fixed = 0

for milestone_number in range(8, 21):
    milestone = progress / f"{milestone_number:02d}"

    for relative in targets:
        path = milestone / relative

        if not path.exists():
            continue

        original = path.read_bytes()

        # Remove trailing spaces/tabs/blank lines,
        # then ensure exactly one final newline.
        cleaned = original.rstrip(b" \t\r\n") + b"\n"

        if cleaned != original:
            path.write_bytes(cleaned)
            print(f"fixed: {path}")
            fixed += 1

print(f"\nFixed {fixed} file(s).")