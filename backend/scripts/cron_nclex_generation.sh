#!/usr/bin/env bash
# NCLEX question generation + import — runs every 30 min via cron.
# Picks next pending NURSE module, generates ~40 questions, imports to DB.
# Exits cleanly when all keys are rate-limited; cron retries 30 min later.

set -euo pipefail

LOG_PREFIX="[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] NCLEX-CRON"
echo "$LOG_PREFIX starting"

# Generate the next pending module
if docker exec medmind_backend python -m app.scripts.generate_nclex_questions --next; then
    echo "$LOG_PREFIX generation OK — importing new questions"
    docker exec medmind_backend python -m app.scripts.import_nclex_questions
    echo "$LOG_PREFIX import OK"
else
    EXIT_CODE=$?
    echo "$LOG_PREFIX generation exited with code $EXIT_CODE (rate-limited or no pending modules)"
fi

echo "$LOG_PREFIX done"
