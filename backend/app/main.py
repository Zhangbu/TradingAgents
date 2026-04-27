from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.analysis import router as analysis_router
from backend.app.api.routes.audit import router as audit_router
from backend.app.api.routes.automation import router as automation_router
from backend.app.api.routes.brokers import router as brokers_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.orders import router as orders_router
from backend.app.api.routes.trade_intents import router as trade_intent_router
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

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(analysis_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(trade_intent_router, prefix=settings.api_prefix)
app.include_router(orders_router, prefix=settings.api_prefix)
app.include_router(automation_router, prefix=settings.api_prefix)
app.include_router(brokers_router, prefix=settings.api_prefix)
