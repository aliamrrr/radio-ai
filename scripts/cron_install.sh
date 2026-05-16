#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$REPO_DIR/.venv/bin/python"
LOG_FILE="$REPO_DIR/logs/pipeline.log"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "Error: venv not found at $VENV_PYTHON. Run ./scripts/setup.sh first."
  exit 1
fi

mkdir -p "$REPO_DIR/logs"

CRON_LINE="0 0 * * * cd $REPO_DIR && $VENV_PYTHON -m pipeline.run_daily >> $LOG_FILE 2>&1"

echo "Installing cron job:"
echo "  $CRON_LINE"
echo ""

# Add to crontab if not already present
(crontab -l 2>/dev/null | grep -v "pipeline.run_daily"; echo "$CRON_LINE") | crontab -

echo "Cron job installed. Verify with: crontab -l"
echo ""
echo "The pipeline will run every night at midnight (system time)."
echo "To adjust the time, edit the cron expression. Current: '0 0 * * *' = midnight."
echo "For timezone awareness, consider: TZ=Europe/Paris crontab"
