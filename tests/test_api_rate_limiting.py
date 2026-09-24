from pathlib import Path

from fastapi.testclient import TestClient

from mobility_control_tower.api.app import create_app
from mobility_control_tower.api.rate_limit import FixedWindowRateLimiter
from mobility_control_tower.security import create_access_token


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_fixed_window_limiter_is_deterministic_and_resets() -> None:
    clock = Clock()
    limiter = FixedWindowRateLimiter(limit=2, window_seconds=10, clock=clock)
    assert limiter.check("operator").allowed
    assert limiter.check("operator").allowed
    denied = limiter.check("operator")
    assert not denied.allowed
    assert denied.retry_after_seconds == 10
    clock.now += 10
    assert limiter.check("operator").allowed


def test_authenticated_operator_mutations_return_429_without_leaking_details(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "rate-limit-test-secret")
    clock = Clock()
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=30, clock=clock)

    class FakeEvaluationEngine:
        def __init__(self, **kwargs):
            pass

        def evaluate(self, **kwargs):
            return type("Result", (), {"evaluation_id": "one", "status": "success", "counts": {}, "errors": []})()

    import mobility_control_tower.api.routes as route_module

    monkeypatch.setattr(route_module, "IncidentEvaluationEngine", FakeEvaluationEngine)
    monkeypatch.setattr(route_module, "evaluation_result_to_dict", lambda result: {"evaluation_id": result.evaluation_id, "status": result.status})
    client = TestClient(create_app(None, rate_limiter=limiter))
    token = create_access_token("operator-one", {"admin"}, expires_in_seconds=60)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post("/v1/incidents/evaluate", headers=headers).status_code == 200
    limited = client.post("/v1/incidents/evaluate", headers=headers)
    assert limited.status_code == 429
    assert limited.json() == {"detail": "request rate limit exceeded"}
    assert limited.headers["Retry-After"] == "30"


def test_authentication_failures_do_not_consume_or_reveal_rate_limit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "rate-limit-test-secret")
    limiter = FixedWindowRateLimiter(limit=1, window_seconds=30, clock=lambda: 100.0)
    client = TestClient(create_app(None, rate_limiter=limiter))

    first = client.post("/v1/incidents/evaluate", headers={"Authorization": "Bearer invalid"})
    second = client.post("/v1/incidents/evaluate", headers={"Authorization": "Bearer invalid"})
    assert first.status_code == second.status_code == 401
    assert first.json() == second.json() == {"detail": "authentication required"}


def test_expired_and_insufficient_scope_tokens_use_the_same_generic_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MCT_AUTH_SECRET", "rate-limit-test-secret")
    client = TestClient(create_app(None))
    expired = create_access_token("old", {"admin"}, expires_in_seconds=-1)
    reader = create_access_token("reader", {"operations:read"}, expires_in_seconds=60)
    responses = [
        client.post("/v1/incidents/evaluate", headers={"Authorization": f"Bearer {expired}"}),
        client.post("/v1/incidents/evaluate", headers={"Authorization": f"Bearer {reader}"}),
    ]
    assert [response.status_code for response in responses] == [401, 401]
    assert all(response.json() == {"detail": "authentication required"} for response in responses)
