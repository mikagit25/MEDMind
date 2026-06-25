#!/bin/bash
# Запускает загрузку видео с двух YouTube аккаунтов параллельно
# Аккаунт 1: client_secret.json + youtube_token.json
# Аккаунт 2: client_secret_account2.json + youtube_token_account2.json

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MEDMIND_DIR="/opt/medmind"
UPLOADER="$SCRIPT_DIR/youtube_uploader.py"

echo "=== MedMind Dual Account Upload ==="
echo "$(date)"

# Аккаунт 1 — первые N статей
echo ""
echo ">>> Аккаунт 1 (первичный)..."
YT_CLIENT_SECRET="$MEDMIND_DIR/client_secret.json" \
YT_TOKEN="$MEDMIND_DIR/youtube_token.json" \
python3 "$UPLOADER" --batch --limit 6 --lang en &

PID1=$!

# Пауза 15 сек чтобы не конкурировать за одни и те же статьи
sleep 15

# Аккаунт 2 — испанский язык, отдельный tracking файл
echo ""
echo ">>> Аккаунт 2 (испанский)..."
YT_CLIENT_SECRET="$MEDMIND_DIR/client_secret_account2.json" \
YT_TOKEN="$MEDMIND_DIR/youtube_token_account2.json" \
YT_TRACKING="$MEDMIND_DIR/youtube_uploaded_es.json" \
python3 "$UPLOADER" --batch --limit 6 --lang es &

PID2=$!

# Ждём оба процесса
wait $PID1
STATUS1=$?
wait $PID2
STATUS2=$?

echo ""
echo "=== Готово ==="
echo "Аккаунт 1: $([ $STATUS1 -eq 0 ] && echo 'OK' || echo 'ОШИБКА')"
echo "Аккаунт 2: $([ $STATUS2 -eq 0 ] && echo 'OK' || echo 'ОШИБКА')"
