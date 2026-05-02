#!/bin/bash
# MEDMind — clean startup script
# Run from Terminal.app: bash /Volumes/one/MEDMind/start.sh

set -e
PROJ="/Volumes/one/MEDMind"

echo "=== Killing stale processes ==="
pkill -f "next" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
sleep 2

echo "=== Checking Docker / PostgreSQL ==="
if ! docker ps | grep -q medmind-pg; then
  echo "Starting medmind-pg..."
  docker start medmind-pg || docker run -d \
    --name medmind-pg \
    -e POSTGRES_USER=medmind \
    -e POSTGRES_PASSWORD=medmind_secret \
    -e POSTGRES_DB=medmind \
    -p 5432:5432 \
    postgres:16
fi
echo "PostgreSQL: OK"

echo "=== Checking Redis ==="
redis-cli ping 2>/dev/null || brew services start redis
echo "Redis: OK"

echo "=== Starting Backend (port 8000) ==="
cd "$PROJ/backend"
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

echo "=== Waiting for backend to be ready ==="
for i in {1..15}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend: READY"
    break
  fi
  echo "  waiting... ($i/15)"
  sleep 2
done

echo "=== Clearing Next.js cache ==="
rm -rf "$PROJ/frontend/.next"
echo "Cache cleared"

echo "=== Starting Frontend (port 3000) ==="
cd "$PROJ/frontend"
# Run in foreground so you can see output and Ctrl+C to stop
echo ""
echo "============================================"
echo " Backend:  http://localhost:8000"
echo " Frontend: http://localhost:3000"
echo " Press Ctrl+C to stop frontend"
echo "============================================"
echo ""
npm run dev
