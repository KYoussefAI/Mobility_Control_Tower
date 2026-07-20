"""Minimal scoped bearer-token security for local operator workflows."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any


class AuthenticationError(ValueError):
    pass


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: set[str]
    expires_at: int


def _secret() -> str:
    secret = os.getenv("MCT_AUTH_SECRET")
    profile = os.getenv("MCT_PROFILE", "local")
    if secret:
        return secret
    if profile in {"local", "demo"}:
        return "local-demo-secret-change-me"
    raise RuntimeError("MCT_AUTH_SECRET must be configured outside local/demo profiles")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_access_token(subject: str, scopes: set[str], *, expires_in_seconds: int = 900) -> str:
    payload = {"sub": subject, "scopes": sorted(scopes), "exp": int(time.time()) + expires_in_seconds}
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def verify_access_token(token: str, required_scopes: set[str] | None = None) -> Principal:
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(_secret().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise AuthenticationError("invalid token")
        payload: dict[str, Any] = json.loads(_unb64(body))
    except Exception as exc:
        raise AuthenticationError("invalid token") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise AuthenticationError("expired token")
    scopes = set(payload.get("scopes", []))
    required = required_scopes or set()
    if not required.issubset(scopes) and "admin" not in scopes:
        raise AuthenticationError("insufficient scope")
    return Principal(subject=str(payload.get("sub", "operator")), scopes=scopes, expires_at=int(payload["exp"]))


def redact_secret(value: str) -> str:
    return value[:4] + "..." if value else ""
