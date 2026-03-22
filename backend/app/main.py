"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agents import router as agents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.autonomous import router as autonomous_router
from app.api.routes.batch import router as batch_router
from app.api.routes.call_brief import router as call_brief_router
from app.api.routes.call_outcomes import router as call_outcomes_router
from app.api.routes.call_session import router as call_session_router
from app.api.routes.call_session import ws_router as call_session_ws_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.leads import router as leads_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.personas import router as personas_router
from app.api.routes.scripts import router as scripts_router
from app.api.routes.webhooks import router as webhooks_router
from app.core.config import settings
from app.core.rate_limit import setup_rate_limiting

_scheduler: Any = None


def _start_scheduler() -> None:
    """Start the autonomous BDR pipeline scheduler (2 AM ET daily)."""
    global _scheduler  # noqa: PLW0603

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            _run_autonomous_pipeline,
            CronTrigger(hour=2, timezone="US/Eastern"),
            id="autonomous_bdr_pipeline",
            name="Nightly BDR Pipeline",
            replace_existing=True,
        )
        _scheduler.start()
        print("Autonomous BDR scheduler started (2 AM ET daily)")
    except ImportError:
        print("APScheduler not installed — autonomous scheduling disabled")
    except Exception as e:
        print(f"Scheduler startup failed: {e}")


def _stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    global _scheduler  # noqa: PLW0603

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


async def _run_autonomous_pipeline() -> None:
    """Cron callback: run the autonomous BDR pipeline."""
    try:
        from app.services.autonomous.runner import autonomous_runner

        await autonomous_runner.run()
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Scheduled autonomous run failed")


def _validate_production_secrets() -> None:
    """Crash on startup if production is running with unsafe defaults."""
    if settings.environment != "production":
        return

    errors: list[str] = []

    if settings.jwt_secret_key == "change-me-in-production":
        errors.append("JWT_SECRET_KEY is still the default value")

    if not settings.epiphan_api_key:
        errors.append("EPIPHAN_API_KEY is not set")

    if settings.epiphan_api_key and settings.jwt_secret_key == settings.epiphan_api_key:
        errors.append("JWT_SECRET_KEY and EPIPHAN_API_KEY must be different values")

    if errors:
        raise SystemExit(
            "FATAL: Production secret validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.version}")
    print(f"Environment: {settings.environment}")
    _validate_production_secrets()

    # Start autonomous pipeline scheduler
    _start_scheduler()

    yield

    # Shutdown
    _stop_scheduler()
    print("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-powered sales intelligence for Epiphan BDR team",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (100 req/min per IP)
setup_rate_limiting(app)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "operational",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(auth_router)  # Already has /api/auth prefix - Token issuance (public)
app.include_router(scripts_router, prefix="/api/scripts", tags=["scripts"])
app.include_router(personas_router, prefix="/api/personas", tags=["personas"])
app.include_router(competitors_router, prefix="/api/competitors", tags=["competitors"])
app.include_router(leads_router, prefix="/api", tags=["leads"])
app.include_router(agents_router)  # Already has /api/agents prefix
app.include_router(call_brief_router)  # Already has /api/agents prefix - Call prep briefs
app.include_router(batch_router)  # Already has /api/batch prefix
app.include_router(webhooks_router)  # Already has /api/webhooks prefix - PHONES ARE GOLD!
app.include_router(call_outcomes_router)  # Already has /api/call-outcomes prefix - Close the feedback loop
app.include_router(monitoring_router)  # Already has /api/monitoring prefix - Track the gold spend!
app.include_router(call_session_router)  # Already has /api/call-session prefix - Voice AI REST fallback
app.include_router(call_session_ws_router)  # WebSocket: /ws/call-session - Voice AI live call support
app.include_router(autonomous_router)  # Already has /api/autonomous prefix - Nightly BDR pipeline
