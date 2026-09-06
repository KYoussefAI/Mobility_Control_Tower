from mobility_control_tower.api.routes import router


def test_static_api_routes_are_registered() -> None:
    paths = {route.path for route in router.routes}

    assert {
        "/health",
        "/metadata",
        "/static/network-overview",
        "/static/top-routes",
    }.issubset(paths)
