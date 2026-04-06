# MedMind AI — Project State (Session Recovery File)

> **CRITICAL**: Read this file first at the start of EVERY new session to restore context.
> Updated every time meaningful work is done.

---

## 🟢 Current Status
**Phase:** 3 — Feature Completion  
**Last Updated:** 2026-04-06  
**Next Action:** Testing phase — run backend + frontend, import VET modules, end-to-end QA. All features implemented.

---

## ✅ COMPLETED (as of 2026-04-03)

### Infrastructure
- PostgreSQL running in Docker (`medmind-pg`, PG 9.6, port 5432)
- Redis running locally (port 6379, no auth)
- 82 modules imported from JSON files
- Backend running on port 8000 with FastAPI

### Backend API — DONE
- Phase 1: All models, schema, config, security ✅
- Phase 2 (Auth): register, login, refresh, /me ✅ (logout MISSING)
- Phase 3 (Content): specialties, modules, lessons, flashcards, MCQ, cases, drugs ✅
- Phase 4 (Progress): lesson/complete, flashcard/review, mcq/answer, stats, SM-2 ✅
- Phase 5 (AI): /ai/ask, /ai/conversations, PubMed search, 4 modes ✅

### Frontend — DONE
- Next.js 14 scaffold + Tailwind ✅
- Login, Register, Onboarding (5-step) ✅
- Dashboard, Modules, AI Tutor, Flashcards, Cases, Drugs, Progress, Settings ✅

### ENV / Keys
- DATABASE_URL=postgresql+asyncpg://medmind:medmind_secret@localhost:5432/medmind
- REDIS_URL=redis://localhost:6379/0
- JWT_SECRET_KEY=5b009c8c3671c50b8805311139853654b71f584872502018e917d42ec2813aa5
- ANTHROPIC_API_KEY=sk-ant-your-key-here ← ⚠️ NEEDS REAL KEY
- ALLOWED_ORIGINS=["http://localhost:3000"]
- MODULES_DIR=/Volumes/one/MEDMind/Modules

### Start Commands (run in Terminal.app NOT VS Code terminal)
```bash
bash /Volumes/one/MEDMind/start.sh       # starts everything
# or manually:
cd /Volumes/one/MEDMind/frontend && npm run dev   # frontend port 3000
cd /Volumes/one/MEDMind/backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000
```

---

## 📋 REMAINING TASKS (Priority Order)

### P0 — Must have before launch
| # | Task | File(s) | Status |
|---|------|---------|--------|
| A | Landing page | `frontend/app/page.tsx` | ✅ DONE |
| B | Auth logout endpoint | `backend/app/api/v1/routes/auth.py` | ✅ DONE |
| C | Auth rate limiting | `backend/app/api/v1/routes/auth.py` | ✅ DONE |
| D | AI rate limiting by tier | `backend/app/api/v1/routes/ai.py` | ✅ DONE |
| E | Stripe payments backend | `backend/app/api/v1/routes/payments.py` | ✅ DONE |
| F | Stripe payments frontend | `frontend/app/(app)/pricing/page.tsx` | ✅ DONE |

### P1 — Important  
| # | Task | File(s) | Status |
|---|------|---------|--------|
| G | Full-text search `/search` | `backend/app/api/v1/routes/content.py` | ✅ DONE |
| H | forgot-password flow | `backend/app/api/v1/routes/auth.py` | ✅ DONE |
| I | Streaming SSE for AI | `backend/app/api/v1/routes/ai.py` | ✅ DONE |
| J | Admin panel | `backend/app/api/v1/routes/admin.py` + `frontend/app/(app)/admin/page.tsx` | ✅ DONE |

### P2 — Nice to have
| # | Task | Status |
|---|------|--------|
| K | Dark mode toggle | ✅ DONE |
| L | Vet mode backend + species dosing | ✅ DONE |
| M | Progress history real data | ✅ DONE |
| N | Vet modules content | ✅ DONE — 4 modules: VET-001…004 |
| O | Mobile app (React Native Expo) | ✅ DONE — `/mobile/` (package.json, Expo Router, 4 screens, WatermelonDB offline sync, SSE AI, auth) |

---

## 🔧 Known Fixes Applied This Session
- passlib→bcrypt direct (passlib 1.7.4 incompatible with bcrypt≥4.0)
- pgvector gated on PGVECTOR_ENABLED=1 env var (PG 9.6 doesn't support it)
- UUID seed fix + is_active=true in specialties seed
- presentation field JSON serialized on import
- next/font/google removed (was blocking compilation)
- NEXT_TELEMETRY_DISABLED=1 to prevent startup hang
- **2026-04-04:** anthropic 0.88.0 partial install fixed (removed ~nthropic broken dist-info)
- **2026-04-04:** apscheduler added to venv (requirements.txt updated to `>=3.10.4`)
- **2026-04-04:** react-hot-toast reinstalled (missing dist/index.d.ts causing TS error)
- **2026-04-04:** Admin panel built — `GET/PATCH /api/v1/admin/stats|users|modules` + frontend `/admin`
- **2026-04-06:** Backend bugs fixed — `ClinicalCase.explanation` AttributeError (use teaching_points); `ai.py` SSE stream `async with db.begin()` InvalidRequestError (remove ctx mgr, plain add+commit)
- **2026-04-06:** Frontend bugs fixed — flashcards `front/back→question/answer`; cases page full rewrite (wrong fields+data); lesson content `LessonContentRenderer` for JSONB; progress weaknesses data shape
- **2026-04-06:** VET modules created — `module_VET-001.json` (Small Animal Internal Med), `module_VET-002.json` (Large Animal Med), `module_VET-003.json` (Veterinary Pharmacology), `module_VET-004.json` (Vet Emergency & Critical Care) — 12 lessons, 32 flashcards, 20 MCQs, 4 clinical cases
- **2026-04-06:** `import_modules.py` — added `"Veterinary": "veterinary"` to SPECIALTY_CODE_MAP
- **2026-04-06:** Alembic migration `0001_initial_schema.py` — complete rewrite (UUID PKs, correct column names, 23 tables including courses)
- **2026-04-06:** `courses.py` — not mounted in main.py (added); route ordering bug fixed (`/join`+`/enrolled` before `/{course_id}`)
- **2026-04-06:** `search/page.tsx` — fixed data shape mismatch (normalize `{modules,lessons}` to flat array); fixed lesson href
- **2026-04-06:** `progress.py` `get_stats` — fixed hardcoded zeros for `lessons_completed`, `mcqs_answered`, `correct_rate`; added `modules_started` field
- **2026-04-06:** `progress/page.tsx` history — fixed display format (day-aggregates vs event list)
- **2026-04-06:** Deleted duplicate `quiz/[moduleId]/page.tsx` (conflict with `quiz/[id]/page.tsx`)
- **2026-04-06:** `GET /progress/modules` — реализован (Task 4.5); добавлена секция "My Modules" в progress/page.tsx
- **2026-04-06:** Email сервис — полностью готов (SMTP + dev fallback + welcome + reset); страница /reset-password существует
- **2026-04-06:** OAuth2 Google — backend (`GET /auth/google` + `GET /auth/google/callback` в auth.py) + frontend (success handler + кнопки в login/register)
- **2026-04-06:** Mobile bugs fixed — (1) `GET /progress/flashcards/due` endpoint added to backend; (2) flashcards.tsx `c.front/c.back→c.question/c.answer`; (3) database.ts sync `fc.front/back→fc.question/answer`; (4) `authApi.register` now sends all required fields; (5) register.tsx rewritten with last name, role picker, GDPR consent checkboxes
- **2026-04-06:** `.env.example` updated with Google OAuth, email, and AI fallback vars; `backend/.env` gets `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` entries

---

## 📁 Project Layout
```
/Volumes/one/MEDMind/
├── Modules/               ← 70+ ready JSON modules (DO NOT MODIFY)
│   ├── medmind_registry.json
│   ├── module_CARDIO-001.json … module_THERAPY-012.json
├── backend/               ← FastAPI Python backend
│   ├── app/
│   │   ├── main.py
│   │   ├── core/          ← config, security, database
│   │   ├── models/        ← SQLAlchemy models
│   │   ├── schemas/       ← Pydantic schemas
│   │   ├── api/v1/        ← API routers
│   │   ├── services/      ← business logic, AI, PubMed
│   │   └── scripts/       ← import_modules.py
│   ├── alembic/           ← DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              ← Next.js 14 App Router
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml     ← PostgreSQL + Redis + pgvector
├── medmind-v2.html        ← UI REFERENCE (do not ship as-is)
├── docs/                  ← All documentation
│   ├── DEVPLAN.md
│   ├── TASKS.md
│   ├── ERRORS_LOG.md
│   ├── PROMPTS.md
│   └── DB_SCHEMA.sql
└── PROJECT_STATE.md       ← THIS FILE
```

---

## ✅ Completed Milestones
- [x] TZ read and analyzed
- [x] 70 JSON modules reviewed — structure confirmed
- [x] Documentation files created (DEVPLAN, TASKS, ERRORS_LOG, PROMPTS)
- [x] Docker-compose file created (PostgreSQL 15 + pgvector, Redis 7)
- [x] Database schema SQL created
- [x] Backend skeleton created (FastAPI, SQLAlchemy 2.0 async)
- [x] Frontend skeleton created (Next.js 14)
- [x] Module import script created

---

## 🔧 Tech Stack (Confirmed)
| Layer | Tech | Notes |
|-------|------|-------|
| Backend | FastAPI 0.111 + Python 3.11 | Async |
| ORM | SQLAlchemy 2.0 + Alembic | Async sessions |
| DB | PostgreSQL 15 + pgvector | Docker |
| Cache | Redis 7 | Rate limiting + AI cache |
| AI | Claude API (Haiku/Sonnet routing) | |
| Frontend | Next.js 14 App Router + TailwindCSS | |
| Auth | JWT + bcrypt + OAuth2 | |
| Payments | Stripe | Subscriptions |
| Mobile | React Native Expo | Phase 4 |

---

## 🔑 Key Design Decisions
1. **Single HTML file for MVP demo** — `medmind-v2.html` is the UI reference
2. **Module import is idempotent** — re-running won't duplicate data
3. **AI routing**: Free→Ollama, Student simple→Haiku, Complex→Sonnet
4. **pgvector** for semantic search on lesson embeddings
5. **SM-2 algorithm** for spaced repetition (flashcards)
6. **GDPR compliance** — email encrypted, consent required

---

## 📋 Current Phase Tasks
See `docs/TASKS.md` for full task list with statuses.

---

## ⚠️ Known Issues / Blockers
See `docs/ERRORS_LOG.md` for error tracking.

---

## 🔐 Environment Variables Needed
```env
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://medmind:secret@localhost:5432/medmind
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET_KEY=generate-random-256-bit
STRIPE_SECRET_KEY=sk_...
PUBMED_API_KEY=optional
AWS_ACCESS_KEY=for-S3-storage

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_...
```

---

## 📦 Module Inventory
- **8 Base modules**: BASE-CARDIO-ANATOMY-001, BASE-RESP-PHYSIO-002, BASE-NEURO-ANATOMY-003, BASE-PHARMA-001, BASE-LAB-DIAGNOSTICS-005, BASE-ECG-006, BASE-RADIOLOGY-007, BASE-EMERGENCY-008
- **10 Cardiology**: CARDIO-001 … CARDIO-010
- **12 Therapy**: THERAPY-001 … THERAPY-012
- **10 Neurology**: NEURO-001 … NEURO-010
- **10 Surgery**: SURG-001 … SURG-010
- **11 Pediatrics**: PEDS-001 … PEDS-011
- **9 OB/GYN**: OB-001 … OB-009
- **4 VET modules**: VET-001 (Small Animal Internal Med), VET-002 (Large Animal Med), VET-003 (Vet Pharmacology), VET-004 (Vet Emergency)
- **Pending**: PSYCH, ANES, ONC, DERM (not yet created)

---

## 🗂 Subscription Tiers
| Tier | Price | AI Requests | Content |
|------|-------|-------------|---------|
| Free | $0 | 5/day | 8 base modules |
| Student | $15/mo | 50/day | All medical |
| Pro | $40/mo | Unlimited | All incl. vet |
| Clinic | $199/mo | 10 users unlimited | All + analytics |
| Lifetime | $299 one-time | Unlimited | All forever |
