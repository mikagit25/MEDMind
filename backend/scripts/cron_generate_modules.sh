#!/usr/bin/env bash
# Cron wrapper for module generation.
# Add to crontab:  crontab -e
#   0 * * * * /opt/medmind/backend/scripts/cron_generate_modules.sh >> /tmp/module_queue.log 2>&1

set -euo pipefail

ENV_FILE="/opt/medmind/backend/.env"

# Load all Groq content-pipeline keys + OpenRouter from .env
if [[ -f "$ENV_FILE" ]]; then
    _load() { grep -E "^${1}=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"'"'" | head -1; }
    export GROQ_KEY_MODULE=$(_load GROQ_KEY_MODULE)
    export GROQ_KEY_MODULE_2=$(_load GROQ_KEY_MODULE_2)
    export GROQ_API_KEY_3=$(_load GROQ_API_KEY_3)
    export GROQ_API_KEY_4=$(_load GROQ_API_KEY_4)
    export GROQ_API_KEY_5=$(_load GROQ_API_KEY_5)
    export GROQ_API_KEY_6=$(_load GROQ_API_KEY_6)
    export GROQ_KEY_VET_ARTICLES=$(_load GROQ_KEY_VET_ARTICLES)
    export GROQ_KEY_VET_MODULES=$(_load GROQ_KEY_VET_MODULES)
    export OPENROUTER_API_KEY=$(_load OPENROUTER_API_KEY)
fi

if [[ -z "${GROQ_KEY_MODULE:-}" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: GROQ_KEY_MODULE not set — aborting"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Cron: starting module generation run ==="
/usr/bin/python3 /opt/medmind/backend/scripts/run_module_queue.py "$@"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Cron: run finished (exit $?) ==="
