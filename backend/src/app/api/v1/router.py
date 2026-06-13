from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.routes import audit, auth, chat, demo, health, invoices, rules, usage

api_router = APIRouter()

# Open routes — no auth required
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Protected routes — require a valid verified JWT
_auth_dep = [Depends(get_current_user)]
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"], dependencies=_auth_dep)
api_router.include_router(rules.router, prefix="/rules", tags=["rules"], dependencies=_auth_dep)
api_router.include_router(audit.router, prefix="/audit", tags=["audit"], dependencies=_auth_dep)
api_router.include_router(chat.router, prefix="/chat", tags=["chat"], dependencies=_auth_dep)
api_router.include_router(demo.router, prefix="/demo", tags=["demo"], dependencies=_auth_dep)
api_router.include_router(usage.router, prefix="/usage", tags=["usage"], dependencies=_auth_dep)
