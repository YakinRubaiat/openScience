"""FastAPI application factory for the openScience REST API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from openscience.api.config import get_settings
from openscience.api.database import get_db, init_db
from openscience.api.deps import register_agents
from openscience.api.middleware.cors import add_cors_middleware
from openscience.api.middleware.logging import RequestLoggingMiddleware
from openscience.api.routes import agents, analysis, auth, sessions
from openscience.api.schemas.response import ErrorResponse
from openscience.core.session import ScienceSession

logger = logging.getLogger("openscience.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    settings = get_settings()
    init_db()
    db = next(get_db())
    try:
        reference = ScienceSession(sandbox_enabled=settings.sandbox_enabled)
        register_agents(db, reference.orchestrator)
    finally:
        db.close()
    yield
    sessions.live_sessions.clear()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        responses={
            422: {"model": ErrorResponse, "description": "Validation error"},
            500: {"model": ErrorResponse, "description": "Internal server error"},
        },
    )

    # Rate limiting
    if settings.rate_limit_enabled:
        limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)

    # CORS and request logging
    add_cors_middleware(app, settings)
    app.add_middleware(RequestLoggingMiddleware)

    # Routes
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(agents.router, prefix=settings.api_prefix)
    app.include_router(sessions.router, prefix=settings.api_prefix)
    app.include_router(analysis.router, prefix=settings.api_prefix)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        """Liveness/readiness probe."""
        return {"status": "ok", "version": settings.version}

    # Error handling
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error": exc.__class__.__name__},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # ``ctx`` may contain raw Exception objects which are not JSON
        # serializable; stringify everything defensively.
        errors = []
        for error in exc.errors():
            safe = {k: (str(v) if k == "ctx" else v) for k, v in error.items()}
            if isinstance(safe.get("ctx"), dict):
                safe["ctx"] = {k: str(v) for k, v in safe["ctx"].items()}
            errors.append(safe)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Request validation failed", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return app


# Module-level app for ``uvicorn openscience.api.main:app``.
app = create_app()
