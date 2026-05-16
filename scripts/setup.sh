#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Setting up AI Radio in: $REPO_DIR"

# Python deps
echo "--- Installing Python dependencies ---"
python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -r "$REPO_DIR/pipeline/requirements.txt"

# Node deps
echo "--- Installing Node dependencies ---"
cd "$REPO_DIR/web"
npm install

# Copy .env if not present
if [ ! -f "$REPO_DIR/.env" ]; then
  cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
  echo ""
  echo "Created .env from .env.example — fill in your API keys before running the pipeline."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Edit .env and fill in your API keys"
echo "  2. python -m pipeline.run_daily --seed-mock   (populate with mock data)"
echo "  3. cd web && npm run dev                       (start the UI)"
