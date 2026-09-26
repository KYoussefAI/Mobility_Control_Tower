from mobility_control_tower.transformations.gtfs_silver import parse_gtfs_time

values = [
    "23:59:59",
    "24:00:00",
    "25:10:00",
    "25:60:00",
    "invalid",
    "",
    None,
]

for value in values:
    print(repr(value), "->", parse_gtfs_time(value))