# MedMind AI — Architecture

## Overview

MedMind AI is a full-stack medical education platform with three clients:

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                              │
│  Next.js 14 (web)   React Native Expo (mobile)             │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS / SSE
┌───────────────────────────▼─────────────────────────────────┐
│                    Nginx reverse proxy                      │
│         TLS termination · static files · rate limit        │
└──────┬────────────────────┬────────────────────────────────┘
       │ /api/v1            │ /  (Next.js)
┌──────▼──────────┐  ┌──────▼──────────┐
│  FastAPI        │  │  Next.js        │
│  (Uvicorn)      │  │  (Node server)  │
└──────┬──────────┘  └─────────────────┘
       │
   ┌───┴────────────────────────────────┐
   │  PostgreSQL 15 + pgvector          │
   │  Redis 7 (cache · rate-limit · SM2)│
   └────────────────────────────────────┘
```

## Backend (FastAPI)

### Key layers

| Layer | Location | Responsibility |
|-------|----------|---------------|
| Routes | `app/api/v1/routes/` | HTTP handler, auth check, input validation |
| Services | `app/services/` | Business logic (AI routing, PDF export, SM-2) |
| Models | `app/models/models.py` | SQLAlchemy ORM (single file, ~800 lines) |
| Schemas | `app/schemas/schemas.py` | Pydantic request/response DTOs |
| Core | `app/core/` | Config, DB session, Redis client, audit log |
| Prompts | `app/prompts/` | LLM prompt templates (tutor, quiz, case) |

### AI routing chain

```
User request
    │
    ▼
sanitize_ai_message()   ← prompt injection guard
    │
    ▼
check_ai_rate_limit()   ← Redis INCR, per-tier daily limit
    │
    ▼
route_ai_request() / route_ai_stream()
    │
    ├─ Anthropic Claude (primary, paid tier)
    ├─ Google Gemini Flash (fallback / free tier)
    ├─ Groq Llama 70B (fallback)
    └─ Ollama (local, free tier)
```

### Spaced repetition (SM-2)

FlashcardReview records per user+card store:
- `ease_factor` (2.5 default)
- `interval_days` (1 → 6 → exponential)
- `repetitions`, `last_quality`, `next_review_at`

`calculate_sm2()` in `progress.py` implements the SuperMemo SM-2 algorithm.

### GDPR compliance

- Email stored as Fernet-encrypted ciphertext (`ENCRYPTION_KEY` env var)
- HMAC-based search index for email lookup without decryption
- Art. 17 (right to erasure): `/compliance/gdpr/delete` anonymises + deletes
- Art. 20 (data portability): `/compliance/gdpr/export` returns full JSON

### Database migrations

Alembic with sequential numbered files:
- `0001_initial.py` — core tables
- `0002_*` … `0007_*` — features added incrementally

Always run `alembic upgrade head` on deploy.

## Frontend (Next.js 14)

### Routing

App Router. Public routes (`/`, `/login`, `/register`) vs protected routes wrapped in `app/(app)/layout.tsx` which checks `useAuthStore`.

### State management

- **Zustand** (`lib/store.ts`): auth user, UI state (sidebar collapse)
- **TanStack Query**: server data caching for modules, progress, etc.
- **Local state**: component-level `useState` for forms, modals

### Analytics

PostHog (`lib/analytics.ts`) — opt-in, no PII, `autocapture: false`.
Sentry (`sentry.client.config.ts`) — error tracking, `sendDefaultPii: false`.

### Performance

- Next.js standalone output → ~50 MB Docker image (vs 2 GB with node_modules)
- Debounced search (350–400 ms) on all search inputs
- Skeleton loaders for all async data
- Sketchfab 3D models: click-to-load (no autoload WebGL)
- `/_next/static/`: 1-year immutable cache header

## Mobile (React Native Expo)

- WatermelonDB for offline-first flashcard storage
- SSE for AI streaming on mobile
- Expo push notifications for study reminders

## Infrastructure

```
Production server (Ubuntu 22.04)
├── Docker Compose (prod)
│   ├── nginx            (ports 80, 443)
│   ├── backend          (internal network)
│   ├── frontend         (internal network)
│   ├── postgres:15-pgvector
│   ├── redis:7-alpine
│   └── certbot          (Let's Encrypt renewal)
└── GitHub Actions CI
    ├── ruff lint + pytest (backend)
    ├── next lint (frontend)
    └── SSH deploy on main merge
```

SSL: Let's Encrypt via certbot webroot, auto-renewed every Sunday 03:00 via cron.

## Observability

- **Sentry**: backend (`sentry-sdk[fastapi]`) + frontend (`@sentry/nextjs`)
- **Health endpoints**: `GET /health` (liveness) · `GET /readiness` (DB + Redis check)
- **Audit log**: `core/audit.py` — writes to `audit_logs` table for admin actions
- **Prometheus / Grafana**: not yet configured (planned)

## Security

| Control | Implementation |
|---------|----------------|
| Auth | JWT (RS-256) + bcrypt, refresh token rotation |
| RBAC | `get_current_user` dep + role checks in routes |
| Rate limiting | slowapi + Redis, per-tier AI limits |
| Prompt injection | `services/prompt_guard.py` pattern matching |
| CORS | strict `ALLOWED_ORIGINS` list, no wildcard |
| Secrets | env vars via pydantic-settings, never in code |
| SQL injection | SQLAlchemy parameterised queries throughout |
| Stripe webhooks | `stripe.Webhook.construct_event()` signature check |
