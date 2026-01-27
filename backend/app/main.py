"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agents import router as agents_router
from app.api.routes.batch import router as batch_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.leads import router as leads_router
from app.api.routes.personas import router as personas_router
from app.api.routes.scripts import router as scripts_router
from app.core.config import settings
from app.core.rate_limit import setup_rate_limiting


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifecycle management."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.version}")
    print(f"Environment: {settings.environment}")

    yield

    # Shutdown
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
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "status": "operational",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include routers
app.include_router(scripts_router, prefix="/api/scripts", tags=["scripts"])
app.include_router(personas_router, prefix="/api/personas", tags=["personas"])
app.include_router(competitors_router, prefix="/api/competitors", tags=["competitors"])
app.include_router(leads_router, prefix="/api", tags=["leads"])
app.include_router(agents_router)  # Already has /api/agents prefix
app.include_router(batch_router)  # Already has /api/batch prefix
