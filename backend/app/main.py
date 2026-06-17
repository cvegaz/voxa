"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_pool, get_pool
from app.routes.extraction_routes import router as extraction_router
from app.routes.template_routes import router as template_router
from app.routes.transcription_routes import router as transcription_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup: create database pool
    app.state.pool = await get_pool()
    yield
    # Shutdown: close database pool
    await close_pool()


app = FastAPI(
    title="Data App API",
    description="Backend API for audio-to-Excel data extraction",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(template_router)
app.include_router(transcription_router)
app.include_router(extraction_router)
