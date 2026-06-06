#!/bin/bash
# Ensure postgres is reachable on localhost:5432.
# If docker-proxy already forwards the port, skip socat.
# Run from cron: */5 * * * * /opt/medmind/ensure_pg_proxy.sh

PG_IP=$(docker inspect medmind_postgres --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null || echo "")

if [ -z "$PG_IP" ]; then
    # Container not networked — ensure alias is registered
    docker network connect --alias postgres medmind_default medmind_postgres 2>/dev/null || true
    PG_IP=$(docker inspect medmind_postgres --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null || echo "")
fi

if [ -z "$PG_IP" ]; then
    echo "$(date) ERROR: postgres container not found or not networked" >> /tmp/socat_pg.log
    exit 1
fi

# Ensure the 'postgres' alias exists in the default network
ALIAS_OK=$(docker network inspect medmind_default --format '{{json .Containers}}' 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(any('postgres' in (v.get('Name','') + ' ' + ' '.join(v.get('Aliases') or [])) for v in d.values()))" 2>/dev/null || echo "False")
if [ "$ALIAS_OK" != "True" ]; then
    docker network disconnect medmind_default medmind_postgres 2>/dev/null || true
    docker network connect --alias postgres medmind_default medmind_postgres 2>/dev/null || true
    echo "$(date) re-registered postgres alias" >> /tmp/socat_pg.log
fi

# If docker-proxy is already forwarding port 5432, nothing to do
if ss -tlnp 2>/dev/null | grep -q ':5432.*docker-proxy\|:5432.*docker'; then
    exit 0
fi

# Check if socat is already running for the correct IP
if pgrep -f "socat.*${PG_IP}:5432" > /dev/null 2>&1; then
    exit 0
fi

# Kill any stale socat on port 5432
pkill -f "socat.*5432" 2>/dev/null || true
sleep 1

# Start fresh socat forwarding
nohup /usr/bin/socat TCP-LISTEN:5432,fork,reuseaddr TCP:${PG_IP}:5432 &>>/tmp/socat_pg.log &
echo "$(date) socat started → ${PG_IP}:5432" >> /tmp/socat_pg.log
