from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import audit, health, invoices, rules

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
