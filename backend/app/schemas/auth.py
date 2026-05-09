from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    auth_enabled: bool
    authenticated: bool
    username: str | None = None
