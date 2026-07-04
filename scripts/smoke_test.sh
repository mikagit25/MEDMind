#!/usr/bin/env bash
# smoke_test.sh — post-deploy health check for MedMind AI
#
# Usage:
#   ./scripts/smoke_test.sh                                      # defaults: medmind.pro
#   BACKEND=http://localhost:8000 FRONTEND=http://localhost:3001 ./scripts/smoke_test.sh  # local
#
# Exit codes: 0 = all green, 1 = one or more checks failed

set -euo pipefail

BACKEND="${BACKEND:-https://medmind.pro}"
FRONTEND="${FRONTEND:-https://medmind.pro}"
TIMEOUT=15   # seconds per request
FAILURES=0

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
NC='\033[0m'

ok()   { echo -e "${GRN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILURES=$((FAILURES + 1)); }
info() { echo -e "${YLW}→${NC} $1"; }

# ─── helper: check URL returns expected HTTP status (accepts space-separated list)
check() {
  local label="$1" url="$2" expected="${3:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null) || code="ERR"
  if echo "$expected" | grep -qw "$code"; then
    ok "$label → $code"
  else
    fail "$label → got $code (expected $expected) — $url"
  fi
}

# ─── helper: POST endpoint ───────────────────────────────────────────────────
check_post() {
  local label="$1" url="$2" body="$3" expected="${4:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" \
    -X POST -H "Content-Type: application/json" -d "$body" "$url" 2>/dev/null) || code="ERR"
  if [[ "$code" == "$expected" ]]; then
    ok "$label → $code"
  else
    fail "$label → got $code (expected $expected) — $url"
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MedMind Smoke Test  $(date '+%Y-%m-%d %H:%M')"
echo "  Backend:  $BACKEND"
echo "  Frontend: $FRONTEND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Backend Health ─────────────────────────────────────────────────────────
echo ""
info "Backend health"
check "GET /health"                   "$BACKEND/health"
check "GET /api/v1/drugs/browse"      "$BACKEND/api/v1/drugs/browse?lang=en&limit=1"
check "GET /api/v1/articles"          "$BACKEND/api/v1/articles?limit=1"
check "GET /api/v1/veterinary/species" "$BACKEND/api/v1/veterinary/species"
check "GET /api/v1/drugs/dosing (canine)" \
      "$BACKEND/api/v1/drugs/dosing?drug=amoxicillin&species=canine"
check_post "POST /api/v1/auth/login (wrong creds → 401)" \
      "$BACKEND/api/v1/auth/login" '{"email":"smoke@medmind.pro","password":"wrongpassword_smoke_123"}' 401

# ── 2. Fetch 10 random drug IDs from API ──────────────────────────────────────
echo ""
info "Fetching drug IDs for frontend smoke test..."
RAW_IDS=$(curl -s --max-time "$TIMEOUT" \
  "$BACKEND/api/v1/drugs/browse?lang=en&limit=30" \
  | python3 -c "
import json,sys,random
try:
    d = json.load(sys.stdin)
    items = d.get('items', d) if isinstance(d, dict) else d
    ids = [x['id'] for x in items if 'id' in x]
    sample = random.sample(ids, min(10, len(ids)))
    print('\n'.join(sample))
except Exception as e:
    print('', end='')
" 2>/dev/null) || RAW_IDS=""

if [[ -z "$RAW_IDS" ]]; then
  fail "Could not fetch drug IDs from API — skipping frontend drug checks"
else
  echo ""
  info "Frontend drug pages (10 random)"
  while IFS= read -r drug_id; do
    [[ -z "$drug_id" ]] && continue
    short="${drug_id:0:8}"
    check "GET /drugs/$short..." "$FRONTEND/drugs/$drug_id"
  done <<< "$RAW_IDS"
fi

# ── 3. Frontend public pages ──────────────────────────────────────────────────
echo ""
info "Frontend public pages"
check "GET / (EN)"                    "$FRONTEND/"
check "GET /drugs"                    "$FRONTEND/drugs"
check "GET /articles"                 "$FRONTEND/articles"
check "GET /learn/topics"             "$FRONTEND/learn/topics"
check "GET /ru/ (Russian locale, follow redirect)" "$FRONTEND/ru/" "200 308 302"
check "GET /ar/ (Arabic locale, follow redirect)"  "$FRONTEND/ar/" "200 308 302"
check "GET /ru/drugs (RU drug list)"  "$FRONTEND/ru/drugs"

# ── 4. Locale-prefixed drug pages ────────────────────────────────────────────
if [[ -n "$RAW_IDS" ]]; then
  FIRST_ID=$(echo "$RAW_IDS" | head -1)
  echo ""
  info "Locale-prefixed drug pages"
  check "GET /ru/drugs/$FIRST_ID" "$FRONTEND/ru/drugs/$FIRST_ID"
  check "GET /ar/drugs/$FIRST_ID" "$FRONTEND/ar/drugs/$FIRST_ID"
  check "GET /de/drugs/$FIRST_ID" "$FRONTEND/de/drugs/$FIRST_ID"
fi

# ── 5. Summary ───────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$FAILURES" -eq 0 ]]; then
  echo -e "${GRN}✓ All checks passed${NC}"
else
  echo -e "${RED}✗ $FAILURES check(s) FAILED${NC}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit "$FAILURES"
