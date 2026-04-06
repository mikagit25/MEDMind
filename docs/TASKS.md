# MedMind AI — Master Task List

> Single source of truth for development tasks.  
> Status: `TODO` | `IN_PROGRESS` | `DONE` | `BLOCKED`

---

## PHASE 1 — Infrastructure & Database ⚙️

| # | Task | Status | Priority |
|---|------|--------|----------|
| 1.1 | Create docker-compose.yml (PostgreSQL 15 + pgvector, Redis 7) | DONE | P0 |
| 1.2 | Create `docs/DB_SCHEMA.sql` — full schema with all tables | DONE | P0 |
| 1.3 | Create backend `requirements.txt` | DONE | P0 |
| 1.4 | Create FastAPI `main.py` entry point | DONE | P0 |
| 1.5 | Create `app/core/config.py` — Settings (pydantic-settings) | DONE | P0 |
| 1.6 | Create `app/core/database.py` — async SQLAlchemy engine | DONE | P0 |
| 1.7 | Create `app/core/security.py` — JWT + bcrypt | DONE | P0 |
| 1.8 | Create all SQLAlchemy models (users, modules, lessons, flashcards…) | DONE | P0 |
| 1.9 | Create Alembic migration for initial schema | DONE | P0 |
| 1.10 | Create `scripts/import_modules.py` — idempotent import of 70 JSON modules | DONE | P0 |
| 1.11 | Test: run docker-compose up, run migration, run import script | TODO | P0 |

## PHASE 2 — Authentication API 🔐

| # | Task | Status | Priority |
|---|------|--------|----------|
| 2.1 | `POST /auth/register` — email+password, returns JWT | DONE | P0 |
| 2.2 | `POST /auth/login` — email+password, returns JWT+refresh | DONE | P0 |
| 2.3 | `POST /auth/refresh` — refresh token rotation | DONE | P0 |
| 2.4 | `POST /auth/logout` — blacklist token in Redis | DONE | P1 |
| 2.5 | `POST /auth/forgot-password` / reset flow | DONE | P1 |
| 2.6 | OAuth2 Google login (next.js frontend handles redirect) | DONE | P2 |
| 2.7 | Middleware: rate limiting (auth endpoints) | DONE | P1 |
| 2.8 | Test auth flow end-to-end | DONE | P0 |

## PHASE 3 — Content API 📚

| # | Task | Status | Priority |
|---|------|--------|----------|
| 3.1 | `GET /specialties` | DONE | P0 |
| 3.2 | `GET /specialties/{id}/modules` | DONE | P0 |
| 3.3 | `GET /modules/{id}` | DONE | P0 |
| 3.4 | `GET /modules/{id}/lessons` | DONE | P0 |
| 3.5 | `GET /lessons/{id}` | DONE | P0 |
| 3.6 | `GET /modules/{id}/flashcards` (+ `?due_only=true`) | DONE | P0 |
| 3.7 | `GET /modules/{id}/mcq` | DONE | P0 |
| 3.8 | `GET /modules/{id}/cases` | DONE | P0 |
| 3.9 | Access control: free tier can only access BASE-* modules | DONE | P0 |
| 3.10 | `GET /search?q=...` — full-text + vector search | DONE | P1 |

## PHASE 4 — Progress & Spaced Repetition 📈

| # | Task | Status | Priority |
|---|------|--------|----------|
| 4.1 | `POST /progress/lesson/{id}/complete` — mark lesson done, award XP | DONE | P0 |
| 4.2 | `POST /progress/flashcard/review` — SM-2 algorithm update | DONE | P0 |
| 4.3 | `POST /progress/mcq/{id}/answer` — evaluate + award XP | DONE | P0 |
| 4.4 | `GET /progress/stats` | DONE | P0 |
| 4.5 | `GET /progress/modules` — returns all modules user started with completion details | DONE | P0 |
| 4.6 | `GET /progress/streak` | DONE | P1 |
| 4.7 | `GET /progress/weaknesses` — recommend weak areas | DONE | P1 |
| 4.8 | SM-2 SQL function `calculate_next_review()` | DONE | P0 |
| 4.9 | Daily XP reset + streak update cron job | ✅ DONE | P1 |

## PHASE 5 — AI Tutor API 🤖

| # | Task | Status | Priority |
|---|------|--------|----------|
| 5.1 | `POST /ai/ask` — smart routing (Free/Haiku/Sonnet) with Redis cache | DONE | P0 |
| 5.2 | PubMed search proxy `GET /search/pubmed?q=...` | DONE | P0 |
| 5.3 | Streaming responses (SSE) for AI answers | DONE | P1 |
| 5.4 | `GET/POST /ai/conversations` — conversation history | DONE | P1 |
| 5.5 | System prompts: tutor, socratic, case, exam modes | DONE | P0 |
| 5.6 | Rate limiting per tier (5/50/unlimited per day) | DONE | P0 |
| 5.7 | AI feedback `POST /ai/feedback` (👍/👎) — message rating + frontend buttons | DONE | P2 |
| 5.8 | Groq (Llama 70B) + Ollama fallback for Free/simple queries | DONE | P2 |

## PHASE 6 — Frontend (Next.js 14) 🖥️

| # | Task | Status | Priority |
|---|------|--------|----------|
| 6.1 | Next.js 14 project scaffold + Tailwind + shadcn/ui | DONE | P0 |
| 6.2 | Landing page (based on HTML prototype design) | DONE | P0 |
| 6.3 | Auth pages: login, register, onboarding (5-step) | DONE | P0 |
| 6.4 | Dashboard — role-based (student/doctor/professor) | DONE | P0 |
| 6.5 | Specialties grid + module list | DONE | P0 |
| 6.6 | Lesson reader page | DONE | P0 |
| 6.7 | Flashcard review (flip animation, SM-2 rating) | DONE | P0 |
| 6.8 | AI Tutor chat page (streaming, PubMed panel) | DONE | P0 |
| 6.9 | Clinical cases page | DONE | P0 |
| 6.10 | MCQ quiz page (`/quiz/[id]`) — shuffled, XP, explanation | DONE | P1 |
| 6.11 | Progress page with charts | DONE | P1 |
| 6.12 | Drug database page | DONE | P2 |
| 6.13 | Settings / profile page | DONE | P1 |
| 6.14 | Dark mode toggle (moon/sun in sidebar, persisted) | DONE | P2 |
| 6.15 | Admin: module management | DONE | P2 |

## PHASE 7 — Payments & Subscriptions 💳

| # | Task | Status | Priority |
|---|------|--------|----------|
| 7.1 | Stripe subscription products setup | DONE | P1 |
| 7.2 | `POST /payments/create-checkout` | DONE | P1 |
| 7.3 | Stripe webhook handler | DONE | P1 |
| 7.4 | Subscription status sync to user.subscription_tier | DONE | P1 |
| 7.5 | Pricing page | DONE | P1 |

## PHASE 8 — Veterinary Mode 🐾

| # | Task | Status | Priority |
|---|------|--------|----------|
| 8.1 | `PUT /user/veterinary-settings` — toggle vet mode | ✅ DONE | P2 |
| 8.2 | Species-specific dosing API | ✅ DONE | P2 |
| 8.3 | VET JSON modules (4 modules created: VET-001…004) | DONE | P2 |

## PHASE 9 — Mobile App 📱

| # | Task | Status | Priority |
|---|------|--------|----------|
| 9.1 | React Native Expo scaffold | ✅ DONE | P3 |
| 9.2 | WatermelonDB offline sync | ✅ DONE | P3 |
| 9.3 | Core screens (dashboard, flashcards, AI tutor) | ✅ DONE | P3 |

---

## Immediate Next Steps (Start Here)
1. `docker-compose up -d` → verify PostgreSQL + Redis running
2. `alembic upgrade head` → apply schema
3. `python scripts/import_modules.py` → import 70 modules
4. Test: `GET /specialties` returns data
5. Build frontend landing page + auth
