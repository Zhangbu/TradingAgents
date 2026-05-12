from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.app.core.auth import (
    SESSION_COOKIE_NAME,
    clear_failed_logins,
    create_session_token,
    get_authenticated_username,
    get_login_client_key,
    is_login_rate_limited,
    register_failed_login,
)
from backend.app.core.config import get_settings
from backend.app.schemas.auth import LoginRequest, SessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SessionResponse)
def login(request: LoginRequest, response: Response, http_request: Request) -> SessionResponse:
    settings = get_settings()
    client_key = get_login_client_key(http_request)

    if not settings.auth_enabled:
        return SessionResponse(
            auth_enabled=False,
            authenticated=True,
            username=settings.auth_username,
        )

    if not settings.auth_password or not settings.auth_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Authentication is enabled, but TRADINGAGENTS_AUTH_PASSWORD or "
                "TRADINGAGENTS_AUTH_SECRET is missing."
            ),
        )

    if is_login_rate_limited(client_key, settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Wait before retrying.",
        )

    username_matches = secrets.compare_digest(request.username, settings.auth_username)
    password_matches = secrets.compare_digest(request.password, settings.auth_password)
    if not (username_matches and password_matches):
        register_failed_login(client_key, settings)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    clear_failed_logins(client_key)
    token = create_session_token(request.username, settings)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_ttl_hours * 3600,
        path="/",
    )
    return SessionResponse(
        auth_enabled=True,
        authenticated=True,
        username=request.username,
    )


@router.post("/logout", response_model=SessionResponse)
def logout(response: Response) -> SessionResponse:
    settings = get_settings()
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return SessionResponse(
        auth_enabled=settings.auth_enabled,
        authenticated=False,
        username=None,
    )


@router.get("/session", response_model=SessionResponse)
def session_status(request: Request) -> SessionResponse:
    settings = get_settings()

    if not settings.auth_enabled:
        return SessionResponse(
            auth_enabled=False,
            authenticated=True,
            username=settings.auth_username,
        )

    username = get_authenticated_username(request, settings)
    return SessionResponse(
        auth_enabled=True,
        authenticated=username is not None,
        username=username,
    )
