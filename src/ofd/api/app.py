"""FastAPI application factory."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ofd import __version__
from ofd.api.routers import (
    admin,
    auth,
    contact,
    health,
    integrations,
    knowledge,
    livekit,
    public_api,
    records,
    voice,
    web,
    widget,
    workspace,
)
from ofd.core import metrics
from ofd.core.config import settings
from ofd.core.exceptions import OFDError
from ofd.core.logging import configure_logging, get_logger
from ofd.services import webhooks as webhooks_svc

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("startup", app=settings.APP_NAME, env=settings.ENV, version=__version__)
    try:
        from ofd.services.knowledge import recover_stale_ingestions

        if recovered := await recover_stale_ingestions():
            logger.warning("recovered_stale_ingestions", count=recovered)
    except Exception as exc:  # no database yet (tests, first boot): nothing to recover
        logger.info("ingest_recovery_skipped", reason=type(exc).__name__)
    yield
    await webhooks_svc.drain(10.0)  # finish in-flight webhook deliveries
    logger.info("shutdown")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="Open-source AI voice receptionist for SMBs.",
        lifespan=lifespan,
    )

    # Open CORS: the embeddable widget runs on arbitrary third-party sites, and the app authenticates
    # with bearer tokens (not cookies), so credentials can stay off.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(request_id=rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = rid
        metrics.incr("http_requests_total", method=request.method, status=str(response.status_code))
        if settings.SECURITY_HEADERS:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return response

    @app.exception_handler(OFDError)
    async def ofd_error_handler(request: Request, exc: OFDError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(workspace.router)
    app.include_router(records.router)
    app.include_router(knowledge.router)
    app.include_router(voice.router)
    app.include_router(admin.router)
    app.include_router(widget.router)
    app.include_router(integrations.router)
    app.include_router(public_api.router)
    app.include_router(contact.router)
    app.include_router(livekit.router)
    app.include_router(web.router)
    return app


app = create_app()
