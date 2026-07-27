#!/usr/bin/env bash
# Cron wrapper — runs translation cron inside medmind_backend container.
# Rotates through all AI provider keys (Groq, Gemini, Cerebras, SambaNova, OpenRouter).
#
# Add to root crontab (crontab -e):
#   */30 * * * * /opt/medmind/backend/scripts/cron_translate_lessons.sh >> /var/log/medmind_translate.log 2>&1

set -euo pipefail

CONTAINER="medmind_backend"
SCRIPT="/app/scripts/translate_cron.py"
BATCH=10   # lessons per run — each lesson × 6 locales = 60 API calls spread across providers

# Ensure script is up to date in container
docker cp /opt/medmind/backend/scripts/translate_cron.py "${CONTAINER}:${SCRIPT}" >/dev/null 2>&1 || true

# Count remaining pending
PENDING=$(docker exec "${CONTAINER}" python3 -c "
import asyncio, sys
sys.path.insert(0, '/app')
from app.core.database import AsyncSessionLocal
from sqlalchemy import text
async def count():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text(\"SELECT count(*) FROM lesson_translations WHERE status='pending'\"))
        print(r.scalar())
asyncio.run(count())
" 2>/dev/null || echo "?")

echo "[$(date '+%Y-%m-%d %H:%M')] Starting translate_cron — pending: ${PENDING}, batch: ${BATCH}"

if [[ "${PENDING}" == "0" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M')] Nothing to translate. Skipping."
    exit 0
fi

docker exec "${CONTAINER}" python3 "${SCRIPT}" --batch "${BATCH}"

echo "[$(date '+%Y-%m-%d %H:%M')] Done."
