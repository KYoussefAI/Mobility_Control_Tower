from mobility_control_tower.dashboard.api_client import ENDPOINTS, fetch_dashboard_data


def test_dashboard_client_requests_static_views(monkeypatch) -> None:
    requested: list[str] = []

    def fake_get_json(base_url: str, endpoint: str, params=None, token=None):
        requested.append(endpoint)
        return {"base_url": base_url, "params": params, "token": token}

    monkeypatch.setattr(
        "mobility_control_tower.dashboard.api_client.get_json", fake_get_json
    )

    result = fetch_dashboard_data("http://api.test")

    for key in ("metadata", "network_overview", "top_routes"):
        assert key in ENDPOINTS
        assert key in result
    assert set(requested) == set(ENDPOINTS.values())
