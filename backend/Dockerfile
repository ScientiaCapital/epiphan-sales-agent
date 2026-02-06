# =============================================================================
# Epiphan Sales Agent - Production Dockerfile
# Multi-stage build with uv for fast, reproducible installs
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build — install dependencies into a virtual environment
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (layer caching — deps change less often than code)
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev deps)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY app/ app/
COPY migrations/ migrations/

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal image with just the app and venv
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Security: run as non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser

WORKDIR /app

# Copy venv and app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
COPY --from=builder /app/migrations /app/migrations

# Ensure venv Python is used
ENV PATH="/app/.venv/bin:$PATH"

# Application config
ENV ENVIRONMENT=production \
    API_HOST=0.0.0.0 \
    API_PORT=8001

EXPOSE 8001

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Run with uvicorn — 4 workers for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
