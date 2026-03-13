#!/bin/bash
set -e
echo "Setting up epiphan-sales-agent..."

# Check for required env
if [ ! -f .env ] && [ ! -f backend/.env ]; then
  echo "Warning: No .env file found. Required vars: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY, APOLLO_API_KEY"
fi

# Install Python backend deps via uv
echo "Installing backend deps..."
cd backend
uv sync

echo "Ready!"
echo "  Start server: cd backend && uv run uvicorn app.main:app --reload --port 8001"
echo "  Run tests:    cd backend && uv run pytest tests/ -v"
echo "  Lint:         cd backend && uv run ruff check ."
echo "  Type check:   cd backend && uv run mypy app/"
