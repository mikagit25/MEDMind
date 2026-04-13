#!/usr/bin/env bash
# MedMind AI — production deploy script
# Usage: ./deploy.sh [--skip-import]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "======================================"
echo "  MedMind AI — Deploy"
echo "======================================"

# 1. Pull latest code
echo "[1/6] Pulling latest code from GitHub..."
git pull origin main

# 2. Check required env files
echo "[2/6] Checking env files..."
if [ ! -f backend/.env.prod ]; then
  echo "ERROR: backend/.env.prod not found."
  echo "Copy backend/.env.prod.example and fill in your secrets."
  exit 1
fi
if [ ! -f .env ]; then
  echo "ERROR: .env not found (for docker-compose.prod.yml POSTGRES_* vars)."
  echo "Create .env with POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB,"
  echo "REDIS_PASSWORD, NEXT_PUBLIC_API_URL"
  exit 1
fi

# 3. Build images
echo "[3/6] Building Docker images..."
docker compose -f docker-compose.prod.yml build --no-cache

# 4. Start services
echo "[4/6] Starting services..."
docker compose -f docker-compose.prod.yml up -d

# 5. Run Alembic migrations
echo "[5/6] Running database migrations..."
sleep 5  # wait for postgres to be healthy
docker compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head

# 6. Import modules (unless --skip-import)
if [[ "${1:-}" != "--skip-import" ]]; then
  echo "[6/6] Importing content modules..."
  docker compose -f docker-compose.prod.yml exec backend \
    python -m scripts.import_modules --dir /app/data/modules
else
  echo "[6/6] Skipping module import (--skip-import)"
fi

echo ""
echo "======================================"
echo "  Deploy complete!"
echo "  Backend:  http://localhost:8000/health"
echo "  Frontend: http://localhost:3000"
echo "======================================"
