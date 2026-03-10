"""
OMNIA — Main FastAPI Application
Entry point for the backend server.

Start with: uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import init_db, close_db
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.websocket import router as ws_router
from app.api.voice import router as voice_router


# ── Logging Setup ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("omnia")


# ── Lifespan (startup/shutdown) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: setup on startup, cleanup on shutdown."""
    logger.info("═" * 60)
    logger.info("  OMNIA AI Assistant — Starting Up")
    logger.info(f"  Environment: {settings.app_env}")
    logger.info(f"  LLM Provider: {settings.active_llm_provider}")
    logger.info(f"  Database: {settings.database_url[:30]}...")
    logger.info("═" * 60)

    # Initialize database tables
    await init_db()
    logger.info("✓ Database initialized")

    yield  # Application is running

    # Shutdown
    await close_db()
    logger.info("OMNIA shutting down. Goodbye!")


# ── FastAPI App ───────────────────────────────────────────────
app = FastAPI(
    title="OMNIA AI Assistant",
    description="Cross-platform autonomous personal AI assistant backend",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS (allow frontend to connect) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Next.js dev server
        "http://localhost:5173",      # Vite dev server
        "http://localhost:1420",      # Tauri dev server
        "https://omnia.app",          # Production domain
        "*",                          # Allow all during development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ─────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ws_router)
app.include_router(voice_router)


# ── Global Exception Handler (dev only) ──────────────────────
if settings.debug:
    from fastapi import Request
    from fastapi.responses import JSONResponse
    import traceback

    @app.exception_handler(Exception)
    async def debug_exception_handler(request: Request, exc: Exception):
        tb = traceback.format_exc()
        logger.error(f"Unhandled exception: {exc}\n{tb}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": tb},
        )


# ── Health Check ──────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "OMNIA AI Assistant",
        "version": "1.0.0",
        "llm_provider": settings.active_llm_provider,
        "environment": settings.app_env,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — welcome message."""
    return {
        "message": "🧠 OMNIA AI Assistant is running",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws",
    }
