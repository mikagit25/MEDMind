#!/bin/bash
# Safe restart script — always uses prod compose to stay on correct networks
set -e
cd /opt/medmind

SERVICE=${1:-""}  # optional: backend, frontend, or empty for all

if [ -z "$SERVICE" ]; then
    docker compose -f docker-compose.prod.yml up -d --no-build
else
    docker compose -f docker-compose.prod.yml up -d --no-build "$SERVICE"
fi

# Give nginx time to re-resolve DNS
sleep 3
docker exec medmind_nginx nginx -s reload 2>/dev/null || true

echo "Done. Container status:"
docker ps --format "{{.Names}}\t{{.Status}}"
