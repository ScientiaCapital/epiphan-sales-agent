"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
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


# Import and include routers
# from app.api.routes import leads, hubspot, clari, agents
# app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
# app.include_router(hubspot.router, prefix="/api/hubspot", tags=["hubspot"])
# app.include_router(clari.router, prefix="/api/clari", tags=["clari"])
# app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
