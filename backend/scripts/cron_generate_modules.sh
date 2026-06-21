#!/usr/bin/env bash
# Cron wrapper for module generation.
# Add to crontab:  crontab -e
#   0 * * * * /opt/medmind/backend/scripts/cron_generate_modules.sh >> /tmp/module_queue.log 2>&1

set -euo pipefail

ENV_FILE="/opt/medmind/backend/.env"

# Load GROQ_KEY_MODULE from .env
if [[ -f "$ENV_FILE" ]]; then
    export GROQ_KEY_MODULE=$(grep -E '^GROQ_KEY_MODULE=' "$ENV_FILE" | cut -d'=' -f2- | tr -d '"'"'" | head -1)
fi

if [[ -z "${GROQ_KEY_MODULE:-}" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: GROQ_KEY_MODULE not set — aborting"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Cron: starting module generation run ==="
/usr/bin/python3 /opt/medmind/backend/scripts/run_module_queue.py "$@"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Cron: run finished (exit $?) ==="
