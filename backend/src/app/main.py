from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.db.session import SessionLocal, run_migrations

logging.basicConfig(
    level=get_settings().log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Run Alembic migrations to head before serving any requests. A failure here
    # means the schema is missing/broken, so the app cannot function — fail loudly
    # (crash boot, fail the deploy) rather than serve 500s against an empty DB.
    run_migrations()

    try:
        from app.seed import DEMO_ORG_ID, seed_demo_user, seed_org

        with SessionLocal() as s:
            seed_demo_user(s)
            seed_org(s, DEMO_ORG_ID)
            s.commit()
    except Exception:
        logger.exception("Seed-on-boot failed — continuing without demo data")
    yield


def create_app() -> FastAPI:
    application = FastAPI(lifespan=lifespan)

    origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    application.include_router(api_router, prefix="/api/v1")

    # In production the built frontend (Vite dist) is copied here and served by the
    # API as a single service. In development the frontend runs on the Vite dev
    # server (which proxies /api to this backend), so this directory is absent.
    static_dir = os.environ.get("IC_STATIC_DIR", "static")
    if Path(static_dir).is_dir():
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="web")

    return application


app = create_app()
