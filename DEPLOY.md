# MedMind AI — Server Deployment Guide

> **Domain:** medmind.pro  
> **Stack:** FastAPI + Next.js + PostgreSQL + Redis + Nginx + Let's Encrypt  
> **Deploy script:** `./deploy.sh`

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Server preparation](#2-server-preparation)
3. [Environment files](#3-environment-files)
4. [First deploy](#4-first-deploy)
5. [Post-deploy checklist](#5-post-deploy-checklist)
6. [Re-deploy (updates)](#6-re-deploy-updates)
7. [Ollama AI setup](#7-ollama-ai-setup)
8. [External services setup](#8-external-services-setup)
9. [SSL management](#9-ssl-management)
10. [Monitoring & logs](#10-monitoring--logs)
11. [Useful management commands](#11-useful-management-commands)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Prerequisites

### Required on the server

```bash
# Docker Engine (>= 24)
curl -fsSL https://get.docker.com | sh
# Add current user to docker group (logout/login after)
sudo usermod -aG docker $USER

# Docker Compose v2 (bundled with modern Docker — verify)
docker compose version

# Git
sudo apt install -y git

# Ollama (local AI — required for AI features)
curl -fsSL https://ollama.com/install.sh | sh
```

### DNS setup (before first deploy)

Point both records to your server IP **before running the deploy script**:

| Record | Name | Value |
|--------|------|-------|
| A | `medmind.pro` | `<SERVER_IP>` |
| A | `www.medmind.pro` | `<SERVER_IP>` |

DNS propagation can take up to 24 hours. Verify with: `dig medmind.pro`

### Minimum server specs

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB (16 GB with qwen3:8b) |
| Disk | 40 GB | 80 GB |
| OS | Ubuntu 22.04 | Ubuntu 22.04/24.04 |

---

## 2. Server preparation

```bash
# Clone repository
git clone https://github.com/your-org/medmind.git /opt/medmind
cd /opt/medmind

# Make deploy script executable
chmod +x deploy.sh
```

---

## 3. Environment files

Two files must exist before deploying. Copy the examples and fill in values:

```bash
cp .env.example .env
cp backend/.env.prod.example backend/.env.prod
```

### `.env` (root — Docker Compose variables)

```bash
# PostgreSQL
POSTGRES_USER=medmind
POSTGRES_PASSWORD=<strong-random-password>
POSTGRES_DB=medmind

# Redis
REDIS_PASSWORD=<strong-random-password>
```

### `backend/.env.prod` (FastAPI application)

```bash
# ── App ───────────────────────────────────────────────────────────────────────
ENVIRONMENT=production
DEBUG=false
ALLOWED_ORIGINS=["https://medmind.pro","https://www.medmind.pro"]
FRONTEND_URL=https://medmind.pro

# ── Database & Redis (auto-set by docker-compose from .env above) ─────────────
# DATABASE_URL is injected by docker-compose.prod.yml — do not set here
# REDIS_URL is injected by docker-compose.prod.yml — do not set here

# ── JWT ───────────────────────────────────────────────────────────────────────
# Generate: openssl rand -hex 32
JWT_SECRET_KEY=<64-char-hex-string>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# ── AI — at least ONE key required in production ──────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...          # claude.ai/settings — primary AI
GEMINI_API_KEY=AIza...                # aistudio.google.com — fallback (free)
GROQ_API_KEY=gsk_...                  # console.groq.com — fallback (free)

# ── Ollama (local free AI — runs on host, not in Docker) ──────────────────────
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:8b                 # qwen3:4b if RAM < 8 GB

# ── Google OAuth2 ─────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=https://medmind.pro/api/v1/auth/google/callback

# ── Stripe ────────────────────────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_...         # or sk_test_... for staging
STRIPE_WEBHOOK_SECRET=whsec_...       # from Stripe Dashboard → Webhooks
STRIPE_PRICE_STUDENT=price_...        # copy from Stripe Dashboard → Products
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_CLINIC=price_...
STRIPE_PRICE_LIFETIME=price_...

# ── PubMed (optional — higher rate limits with key) ───────────────────────────
PUBMED_API_KEY=                       # ncbi.nlm.nih.gov/account/

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@medmind.pro
SMTP_PASSWORD=<app-password>          # Gmail: 16-char App Password
EMAIL_FROM=MedMind AI <noreply@medmind.pro>

# ── Encryption ────────────────────────────────────────────────────────────────
# Generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=<fernet-key>

# ── Media uploads ─────────────────────────────────────────────────────────────
MEDIA_ROOT=/app/data/media
MEDIA_URL=/media

# ── S3 / MinIO (optional — for CDN media storage) ────────────────────────────
USE_S3=false
# AWS_STORAGE_BUCKET_NAME=medmind-media
# AWS_S3_REGION_NAME=eu-west-1
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_S3_CUSTOM_DOMAIN=cdn.medmind.pro

# ── Sentry (optional — error tracking) ───────────────────────────────────────
SENTRY_DSN=https://...@sentry.io/...

# ── Docs (disable in production) ─────────────────────────────────────────────
ENABLE_DOCS=false

# ── SEO ───────────────────────────────────────────────────────────────────────
NEXT_PUBLIC_SITE_URL=https://medmind.pro
```

---

## 4. First deploy

```bash
cd /opt/medmind
./deploy.sh
```

The script will:
1. Check prerequisites and env files
2. Pull latest code from `main`
3. Build Docker images (backend + frontend)
4. Start postgres + redis
5. Obtain Let's Encrypt SSL certificate for medmind.pro and www.medmind.pro
6. Start all services (nginx, backend, frontend, certbot)
7. Run Alembic database migrations
8. Import content modules from `/Modules`
9. Set up weekly SSL auto-renewal cron

Expected time: **10–15 minutes** on first deploy.

---

## 5. Post-deploy checklist

Run these steps **after every first deploy** and after major updates.

### 5.1 Verify all migrations ran

```bash
docker compose -f docker-compose.prod.yml exec backend alembic current
# Should show: head (revision 0015)
```

If not at head:
```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

Migration history:
| # | Description |
|---|-------------|
| 0001 | Initial tables (users, modules, lessons) |
| 0002 | Subscriptions |
| 0003 | Flashcards |
| 0004 | Progress tracking |
| 0005 | Courses |
| 0006 | AI chat history |
| 0007 | Drug database |
| 0008 | Imaging / anatomy |
| 0009 | Clinical cases |
| 0010 | Notifications |
| 0011 | Leaderboard |
| 0012 | Knowledge bank |
| 0013 | Adaptive plan |
| 0014 | Early warning system |
| **0015** | **Lesson/module translations (lesson_translations, module_translations)** |

### 5.2 Import content modules

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.import_modules --dir /app/data/modules
```

Expected: 70+ modules imported. Safe to run multiple times (idempotent).

### 5.3 Seed imaging & anatomy viewers

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python -m scripts.seed_imaging
```

### 5.4 Set up Ollama

See [Section 7](#7-ollama-ai-setup) for full Ollama setup.

Quick start:
```bash
ollama pull qwen3:8b
# Check Ollama is accessible from Docker:
docker compose -f docker-compose.prod.yml exec backend \
  curl -s http://host.docker.internal:11434/api/tags | python3 -m json.tool
```

### 5.5 Configure Stripe webhook

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://medmind.pro/api/v1/payments/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the **Signing secret** → set `STRIPE_WEBHOOK_SECRET` in `backend/.env.prod`
5. Restart backend: `docker compose -f docker-compose.prod.yml restart backend`

### 5.6 Update Google OAuth redirect URI

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Select your OAuth 2.0 Client
3. Under **Authorized redirect URIs**, add:
   ```
   https://medmind.pro/api/v1/auth/google/callback
   ```
4. Remove any localhost redirect URIs used during development

### 5.7 Test email delivery

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python3 -c "
import asyncio
from app.services.email import send_email
asyncio.run(send_email('test@example.com', 'MedMind Test', '<p>Hello</p>'))
print('Email sent')
"
```

### 5.8 Generate ENCRYPTION_KEY (if not done yet)

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output → set as `ENCRYPTION_KEY` in `backend/.env.prod`.

### 5.9 Verify health endpoint

```bash
curl -s https://medmind.pro/health | python3 -m json.tool
# Expected: {"status": "ok", "database": "ok", "redis": "ok"}
```

### 5.10 Check translation service

After publishing a lesson, translations should fire automatically. Check background tasks:
```bash
docker compose -f docker-compose.prod.yml logs backend | grep translation
```

---

## 6. Re-deploy (updates)

### Pull and rebuild (standard update)

```bash
cd /opt/medmind
git pull origin main
./deploy.sh
```

### Quick re-deploy (no image rebuild)

Use when only env vars or config changed:
```bash
./deploy.sh --no-build
```

### Skip module import (faster)

Use when modules haven't changed:
```bash
./deploy.sh --skip-import
```

### Manual service restart

```bash
# Restart individual service
docker compose -f docker-compose.prod.yml restart backend

# Rebuild and restart single service
docker compose -f docker-compose.prod.yml up -d --build backend
```

---

## 7. Ollama AI setup

Ollama runs **on the host machine** (not inside Docker) so it can use GPU if available.

### Install and configure

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull the primary model (requires ~5 GB RAM at runtime)
ollama pull qwen3:8b

# For servers with less than 8 GB RAM:
ollama pull qwen3:4b

# Verify
ollama list
```

### Make Ollama accessible from Docker

By default Ollama only listens on `localhost`. To expose it to Docker containers:

```bash
# Edit Ollama systemd service
sudo systemctl edit ollama
```

Add these lines:
```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Verify accessible from outside
curl http://localhost:11434/api/tags
```

In `backend/.env.prod`:
```bash
OLLAMA_URL=http://host.docker.internal:11434
```

### GPU acceleration (optional)

If the server has an NVIDIA GPU:
```bash
# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
# Ollama will automatically use GPU after restart
```

---

## 8. External services setup

### Anthropic (Claude AI)

1. Get API key at [console.anthropic.com](https://console.anthropic.com)
2. Set `ANTHROPIC_API_KEY=sk-ant-...` in `backend/.env.prod`
3. Used for: AI tutor, lesson translation (Haiku), content generation

### Google Gemini (free fallback)

1. Get free key at [aistudio.google.com](https://aistudio.google.com)
2. Set `GEMINI_API_KEY=AIza...` in `backend/.env.prod`
3. Free tier: 1500 requests/day

### Groq (free fallback)

1. Get free key at [console.groq.com](https://console.groq.com)
2. Set `GROQ_API_KEY=gsk_...` in `backend/.env.prod`
3. Free tier: 14400 requests/day

### Stripe (payments)

1. Create products and prices in [Stripe Dashboard](https://dashboard.stripe.com/products)
2. Create 4 prices: Student Monthly, Pro Monthly, Clinic Monthly, Lifetime
3. Copy price IDs → `STRIPE_PRICE_*` variables
4. Set up webhook → `STRIPE_WEBHOOK_SECRET` (see 5.5)

**Upgrade a user's tier manually (admin/testing):**
```bash
docker compose -f docker-compose.prod.yml exec backend python3 -c "
import asyncio
from app.db.session import get_db
from app.models.models import User
from sqlalchemy import update

async def upgrade():
    async for db in get_db():
        await db.execute(update(User).where(User.email=='user@example.com').values(tier='pro'))
        await db.commit()
        print('Done')

asyncio.run(upgrade())
"
```

### PubMed (medical literature)

1. Register at [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/)
2. Generate API key in account settings
3. Set `PUBMED_API_KEY=...` — upgrades rate limit from 3/sec to 10/sec

### Gmail SMTP

1. Enable 2FA on the Gmail account
2. Go to Google Account → Security → App Passwords
3. Generate a 16-character App Password
4. Set `SMTP_USER` and `SMTP_PASSWORD` in `backend/.env.prod`

---

## 9. SSL management

### Auto-renewal

SSL auto-renewal is set up by `deploy.sh` as a weekly cron (Sundays at 03:00).

Verify cron is active:
```bash
crontab -l | grep medmind
```

### Manual renewal

```bash
./deploy.sh --ssl-only
```

### Check certificate expiry

```bash
docker run --rm \
  -v medmind_letsencrypt_data:/etc/letsencrypt:ro \
  alpine sh -c "cat /etc/letsencrypt/live/medmind.pro/cert.pem" \
  | openssl x509 -noout -dates
```

---

## 10. Monitoring & logs

### Service status

```bash
docker compose -f docker-compose.prod.yml ps
```

### Live logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f postgres
```

### Disk usage

```bash
# Docker volumes
docker system df -v

# Database size
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U medmind -c "SELECT pg_size_pretty(pg_database_size('medmind'));"
```

### Sentry error tracking (optional)

1. Create project at [sentry.io](https://sentry.io)
2. Copy DSN → `SENTRY_DSN=https://...@sentry.io/...` in `backend/.env.prod`
3. Restart backend

---

## 11. Useful management commands

### Database

```bash
COMPOSE="docker compose -f docker-compose.prod.yml"

# Run migrations
$COMPOSE exec backend alembic upgrade head

# Migration status
$COMPOSE exec backend alembic current

# Rollback one migration
$COMPOSE exec backend alembic downgrade -1

# Connect to PostgreSQL
$COMPOSE exec postgres psql -U medmind -d medmind

# Backup database
$COMPOSE exec postgres pg_dump -U medmind medmind > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20260101.sql | $COMPOSE exec -T postgres psql -U medmind -d medmind
```

### Content management

```bash
# Import/re-import modules
$COMPOSE exec backend python -m scripts.import_modules --dir /app/data/modules

# Seed imaging data
$COMPOSE exec backend python -m scripts.seed_imaging

# Re-translate a specific lesson (by lesson ID)
$COMPOSE exec backend python3 -c "
import asyncio
from app.services.translation_service import retranslate_lesson
from app.db.session import get_db

async def run():
    async for db in get_db():
        await retranslate_lesson('LESSON_ID_HERE', 'ru', db)
        print('Done')

asyncio.run(run())
"
```

### User management

```bash
# List all users
$COMPOSE exec postgres psql -U medmind -c "SELECT id, email, tier, created_at FROM users ORDER BY created_at DESC LIMIT 20;"

# Upgrade user tier (student/pro/clinic/lifetime)
$COMPOSE exec postgres psql -U medmind -c \
  "UPDATE users SET tier='pro' WHERE email='user@example.com';"

# Reset user password (generates bcrypt hash)
$COMPOSE exec backend python3 -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'])
print(pwd_context.hash('newpassword123'))
"
# Then: UPDATE users SET hashed_password='<hash>' WHERE email='...';
```

### Cache management

```bash
# Clear Redis cache
$COMPOSE exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB

# Check Redis memory
$COMPOSE exec redis redis-cli -a $REDIS_PASSWORD INFO memory | grep used_memory_human
```

### System maintenance

```bash
# Remove unused Docker images (free disk space)
docker image prune -f

# Full Docker cleanup (WARNING: removes stopped containers, unused volumes)
docker system prune --volumes

# Restart all services
$COMPOSE restart

# Stop all services
$COMPOSE down

# Stop all and remove volumes (DESTRUCTIVE — loses all data)
$COMPOSE down -v
```

---

## 12. Troubleshooting

### Backend won't start

```bash
docker compose -f docker-compose.prod.yml logs backend
```

Common causes:
- Missing required env vars (`DATABASE_URL`, `JWT_SECRET_KEY`, no AI key set)
- Database not ready yet — wait 10 seconds and retry
- Alembic migration error — check migration history

### Nginx returns 502 Bad Gateway

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs nginx
```

Usually means backend or frontend container isn't running. Check their logs.

### SSL certificate error / HTTPS not working

```bash
# Check if certificate exists
docker run --rm -v medmind_letsencrypt_data:/etc/letsencrypt:ro alpine ls /etc/letsencrypt/live/

# Re-issue certificate
./deploy.sh --ssl-only
```

Make sure DNS is pointing to the server before running certbot.

### Translations not firing after publish

1. Check backend logs for `translation` keyword
2. Verify at least one AI key is set (`ANTHROPIC_API_KEY` or `GEMINI_API_KEY`)
3. Check translation status via API:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     https://medmind.pro/api/v1/lessons/<id>/translations
   ```

### Ollama not accessible from backend

```bash
# Test from inside backend container
docker compose -f docker-compose.prod.yml exec backend \
  curl -s http://host.docker.internal:11434/api/tags

# If it fails, check Ollama is binding to 0.0.0.0
systemctl status ollama
```

Make sure `OLLAMA_HOST=0.0.0.0:11434` is set in Ollama's systemd environment (see Section 7).

### Out of disk space

```bash
df -h
docker system df

# Free space
docker image prune -f
docker builder prune -f
```

---

*Last updated: 2026-04-22*
