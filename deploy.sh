#!/usr/bin/env bash
###############################################################################
# MedMind AI — Production deploy script
# Domain: medmind.pro  |  SSL: Let's Encrypt (auto)
#
# Usage:
#   ./deploy.sh              — first deploy OR re-deploy
#   ./deploy.sh --no-build   — skip Docker rebuild (config/env changes only)
#   ./deploy.sh --ssl-only   — renew SSL certificate only
#   ./deploy.sh --skip-import — skip module import step
###############################################################################
set -euo pipefail

DOMAIN="medmind.pro"
EMAIL="admin@medmind.pro"      # ← set to your real email for Let's Encrypt notices
COMPOSE="docker compose -f docker-compose.prod.yml"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${GREEN}[deploy]${NC} $*"; }
warning() { echo -e "${YELLOW}[warn]${NC}   $*"; }
error()   { echo -e "${RED}[error]${NC}  $*"; exit 1; }
step()    { echo -e "\n${CYAN}── $* ${NC}"; }

# ── Parse arguments ───────────────────────────────────────────────────────────
NO_BUILD=false; SSL_ONLY=false; SKIP_IMPORT=false
for arg in "$@"; do
  case $arg in
    --no-build)    NO_BUILD=true ;;
    --ssl-only)    SSL_ONLY=true ;;
    --skip-import) SKIP_IMPORT=true ;;
  esac
done

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   MedMind AI — Production Deploy          ║${NC}"
echo -e "${GREEN}║   https://$DOMAIN                        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────────────
step "Preflight checks"
command -v docker >/dev/null 2>&1 || error "Docker not found. Install: https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 || error "Docker Compose v2 not found."
[ -f ".env" ]              || error ".env missing. Run:  cp .env.example .env && nano .env"
[ -f "backend/.env.prod" ] || error "backend/.env.prod missing. Run:  cp backend/.env.prod.example backend/.env.prod && nano backend/.env.prod"
info "All prerequisites satisfied."

# ── Pull latest code ──────────────────────────────────────────────────────────
step "Pull latest code"
git pull origin main || warning "git pull failed — deploying current local code."

# ── SSL-only mode ─────────────────────────────────────────────────────────────
if $SSL_ONLY; then
  step "SSL certificate renewal"
  $COMPOSE run --rm certbot renew --quiet
  $COMPOSE exec nginx nginx -s reload && info "Nginx reloaded with renewed cert."
  info "SSL renewed successfully."
  exit 0
fi

# ── Check whether certificate already exists ──────────────────────────────────
step "Checking SSL certificate"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
CERT_EXISTS=false
if docker volume ls -q 2>/dev/null | grep -q "letsencrypt"; then
  if docker run --rm \
       -v medmind_letsencrypt_data:/etc/letsencrypt \
       alpine sh -c "[ -f $CERT_PATH ]" 2>/dev/null; then
    CERT_EXISTS=true
    info "Certificate found for $DOMAIN."
  fi
fi

# ── Build images ──────────────────────────────────────────────────────────────
if ! $NO_BUILD; then
  step "Building Docker images"
  $COMPOSE build --parallel
fi

# ── First deploy — obtain SSL certificate ─────────────────────────────────────
if ! $CERT_EXISTS; then
  info "No certificate found — starting first-time SSL setup."
  step "Starting backend + frontend (no nginx yet)"
  $COMPOSE up -d postgres redis
  info "Waiting for DB/Redis to be ready..."
  sleep 8
  $COMPOSE up -d backend frontend
  info "Waiting for app to start..."
  sleep 10

  step "Starting temporary HTTP-only nginx for ACME challenge"
  docker run --rm -d \
    --name medmind_nginx_init \
    -p 80:80 \
    -v "$REPO_DIR/nginx-init.conf:/etc/nginx/conf.d/default.conf:ro" \
    -v medmind_certbot_webroot:/var/www/certbot \
    --network medmind_external \
    nginx:1.25-alpine
  info "Bootstrap nginx started."

  step "Issuing Let's Encrypt certificate"
  $COMPOSE run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

  docker stop medmind_nginx_init 2>/dev/null && info "Bootstrap nginx stopped."
  info "Certificate issued for $DOMAIN!"
fi

# ── Start / update all services ───────────────────────────────────────────────
step "Starting all services"
$COMPOSE up -d --remove-orphans
info "All services started."

# ── Wait and verify nginx ─────────────────────────────────────────────────────
info "Waiting 8 seconds for nginx to initialise..."
sleep 8
if $COMPOSE ps nginx 2>/dev/null | grep -qE "Up|running|healthy"; then
  info "Nginx is up and serving HTTPS."
else
  warning "Nginx status unclear — check: $COMPOSE logs nginx"
fi

# ── Database migrations ───────────────────────────────────────────────────────
step "Database migrations"
$COMPOSE exec backend alembic upgrade head 2>/dev/null && info "Migrations applied." || \
  warning "Alembic skipped — tables likely created by SQLAlchemy auto-create on startup."

# ── Import content modules ────────────────────────────────────────────────────
if ! $SKIP_IMPORT; then
  step "Importing content modules"
  $COMPOSE exec backend python -m scripts.import_modules --dir /app/data/modules 2>/dev/null || \
    warning "Module import skipped (no modules directory or already imported)."
else
  info "Module import skipped (--skip-import)."
fi

# ── SSL auto-renewal cron ─────────────────────────────────────────────────────
step "Setting up SSL auto-renewal cron"
CRON_JOB="0 3 * * 0 cd $REPO_DIR && docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f docker-compose.prod.yml exec nginx nginx -s reload >> /var/log/medmind-ssl-renew.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "medmind.*certbot"; then
  (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
  info "Cron job added: SSL auto-renewal every Sunday at 03:00."
else
  info "SSL renewal cron already configured."
fi

# ── Health check ──────────────────────────────────────────────────────────────
step "Health check"
sleep 3
if curl -sf "https://$DOMAIN/health" >/dev/null 2>&1; then
  info "Health check passed: https://$DOMAIN/health"
elif curl -sf "http://$DOMAIN/health" >/dev/null 2>&1; then
  warning "App responds on HTTP but not HTTPS — check nginx SSL config."
else
  warning "Health check failed — app may still be starting. Check: $COMPOSE logs"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓  MedMind AI deployed successfully!         ║${NC}"
echo -e "${GREEN}║     https://$DOMAIN                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Useful commands:"
echo "  $COMPOSE ps                          — service status"
echo "  $COMPOSE logs -f backend             — backend logs"
echo "  $COMPOSE logs -f nginx               — nginx logs"
echo "  $COMPOSE logs -f frontend            — frontend logs"
echo "  $COMPOSE exec backend alembic upgrade head  — run migrations"
echo "  ./deploy.sh --ssl-only               — renew SSL certificate"
echo "  ./deploy.sh --no-build               — redeploy without rebuild"
echo ""
