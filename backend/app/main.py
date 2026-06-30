"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import close_pool, get_pool
from app.rate_limit import limiter
from app.routes.contact_routes import router as contact_router
from app.routes.extraction_routes import router as extraction_router
from app.routes.template_routes import router as template_router
from app.routes.transcription_routes import router as transcription_router

# Origins allowed to call the API cross-origin. The app frontend is served
# same-origin (Nginx proxies /api), but the public landing page is a separate
# static site on its own origin, so its contact form needs CORS. Comma-separated
# list via LANDING_ORIGINS; defaults to the local dev servers.
_DEFAULT_LANDING_ORIGINS = "http://localhost:5173,http://localhost:4173"
LANDING_ORIGINS = [
    origin.strip()
    for origin in os.getenv("LANDING_ORIGINS", _DEFAULT_LANDING_ORIGINS).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup: create database pool
    app.state.pool = await get_pool()
    yield
    # Shutdown: close database pool
    await close_pool()


app = FastAPI(
    title="Voxa API",
    description="Backend API for audio-to-Excel data extraction",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting (slowapi) — the limiter instance must live on app.state so the
# per-route @limiter.limit decorators can find it.
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=LANDING_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Flatten slowapi's 429 to the frontend error contract."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.",
            "errorCode": "RATE_LIMITED",
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Flatten all HTTP errors to the contract the frontend expects:
    a top-level ``{"detail": str, "errorCode": str}`` in camelCase.

    Routes raise ``HTTPException(detail=ErrorResponse(...).model_dump())``, which
    produces a nested ``{"detail": {"detail": ..., "error_code": ...}}``. We
    unwrap it here so the client never has to deal with nested or snake_case shapes.
    """
    detail = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": detail.get("detail", ""),
                "errorCode": detail.get("error_code", "ERROR"),
            },
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(detail), "errorCode": "ERROR"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI's default 422 puts a list of error objects in ``detail``, which the
    frontend cannot render. Collapse it to a single human-readable string."""
    errors = exc.errors()
    message = "Los datos enviados no son válidos."
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "")
        message = f"{loc}: {msg}".strip(": ") or message
    return JSONResponse(
        status_code=422,
        content={"detail": message, "errorCode": "VALIDATION_ERROR"},
    )


app.include_router(template_router)
app.include_router(transcription_router)
app.include_router(extraction_router)
app.include_router(contact_router)
