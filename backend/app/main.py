from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes.analysis import router as analysis_router
from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.audit import router as audit_router
from backend.app.api.routes.automation import router as automation_router
from backend.app.api.routes.brokers import router as brokers_router
from backend.app.api.routes.diagnostics import router as diagnostics_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.orders import router as orders_router
from backend.app.api.routes.trade_intents import router as trade_intent_router
from backend.app.core.auth import get_authenticated_username
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    if settings.environment == "development"
    else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_api_authentication(request, call_next):
    if not settings.auth_enabled:
        return await call_next(request)

    path = request.url.path
    public_prefixes = {
        f"{settings.api_prefix}/health",
        f"{settings.api_prefix}/auth/login",
        f"{settings.api_prefix}/auth/logout",
        f"{settings.api_prefix}/auth/session",
    }

    if request.method == "OPTIONS" or path in public_prefixes:
        return await call_next(request)

    if path.startswith(settings.api_prefix):
        username = get_authenticated_username(request, settings)
        if username is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required."},
            )

    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' http: https:; "
        "font-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    return response

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(analysis_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(trade_intent_router, prefix=settings.api_prefix)
app.include_router(orders_router, prefix=settings.api_prefix)
app.include_router(automation_router, prefix=settings.api_prefix)
app.include_router(brokers_router, prefix=settings.api_prefix)
app.include_router(diagnostics_router, prefix=settings.api_prefix)
