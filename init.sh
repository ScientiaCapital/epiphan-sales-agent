#!/usr/bin/env bash
set -euo pipefail

echo "Initializing epiphan-sales-agent (Python/FastAPI, uv)..."

if ! command -v uv &>/dev/null; then
  echo "Error: uv is not installed. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

cd "$(dirname "$0")/backend"
uv sync

echo ""
echo "Done."
echo "Start server: cd backend && uv run uvicorn app.main:app --reload --port 8001"
echo "Run tests:    cd backend && uv run pytest tests/ -v"
echo "Lint:         cd backend && uv run ruff check ."
echo "Type check:   cd backend && uv run mypy app/"
