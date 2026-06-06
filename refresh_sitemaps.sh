#!/bin/bash
# Refresh Next.js ISR cache for all sitemaps.
# Should run after daily article/news generation (cron: 05:00).
# Next.js serves stale response + triggers background regen → next hit is fresh.
# We ping twice (with a short pause) so the second pass gets the newly built version.

set -euo pipefail

FRONTEND="http://localhost:3000"
LOG="/opt/medmind/logs/sitemap_refresh.log"
LOCALES=(en ru ar de fr es tr)

echo "$(date '+%Y-%m-%d %H:%M:%S') — sitemap refresh start" >> "$LOG"

for locale in "${LOCALES[@]}"; do
    url="${FRONTEND}/sitemap-${locale}.xml"
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$url" 2>/dev/null || echo "ERR")
    echo "  ${locale}: pass1 → ${status}" >> "$LOG"
done

echo "  waiting 15s for ISR background regen..." >> "$LOG"
sleep 15

for locale in "${LOCALES[@]}"; do
    url="${FRONTEND}/sitemap-${locale}.xml"
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$url" 2>/dev/null || echo "ERR")
    echo "  ${locale}: pass2 → ${status}" >> "$LOG"
done

# Also refresh the sitemap index
curl -s -o /dev/null -w "  index: %{http_code}\n" --max-time 30 "${FRONTEND}/sitemap.xml" >> "$LOG" 2>/dev/null || true

echo "$(date '+%Y-%m-%d %H:%M:%S') — sitemap refresh done" >> "$LOG"
