from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections import deque
from datetime import datetime, timedelta, timezone

from fastapi import Request

from backend.app.core.config import Settings

SESSION_COOKIE_NAME = "tradingagents_session"
_FAILED_LOGIN_ATTEMPTS: dict[str, deque[datetime]] = {}


def create_session_token(username: str, settings: Settings) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auth_session_ttl_hours)
    payload = {
        "sub": username,
        "exp": int(expires_at.timestamp()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _b64encode(payload_bytes)
    signature = _sign(encoded_payload, settings.auth_secret or "")
    return f"{encoded_payload}.{signature}"


def verify_session_token(token: str | None, settings: Settings) -> str | None:
    if not token or not settings.auth_secret:
        return None

    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign(encoded_payload, settings.auth_secret)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except Exception:
        return None

    expires_at = payload.get("exp")
    subject = payload.get("sub")
    if not isinstance(expires_at, int) or not isinstance(subject, str):
        return None

    if expires_at < int(datetime.now(timezone.utc).timestamp()):
        return None

    return subject


def get_authenticated_username(request: Request, settings: Settings) -> str | None:
    if not settings.auth_enabled:
        return settings.auth_username

    token = request.cookies.get(SESSION_COOKIE_NAME)
    return verify_session_token(token, settings)


def is_login_rate_limited(client_key: str, settings: Settings) -> bool:
    attempts = _get_recent_attempts(client_key, settings)
    return len(attempts) >= settings.auth_max_login_attempts


def register_failed_login(client_key: str, settings: Settings) -> None:
    attempts = _get_recent_attempts(client_key, settings)
    attempts.append(datetime.now(timezone.utc))


def clear_failed_logins(client_key: str) -> None:
    _FAILED_LOGIN_ATTEMPTS.pop(client_key, None)


def get_login_client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    client = request.client
    return client.host if client else "unknown"


def _sign(encoded_payload: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _get_recent_attempts(client_key: str, settings: Settings) -> deque[datetime]:
    window_start = datetime.now(timezone.utc) - timedelta(minutes=settings.auth_login_window_minutes)
    attempts = _FAILED_LOGIN_ATTEMPTS.setdefault(client_key, deque())

    while attempts and attempts[0] < window_start:
        attempts.popleft()

    return attempts
