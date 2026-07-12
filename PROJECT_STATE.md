# MedMind AI — Project State (Session Recovery File)

> **CRITICAL**: Read this file first at the start of EVERY new session to restore context.
> Updated every time meaningful work is done.

---

## 🟢 Current Status
**Phase:** V5 Phases 0–6 ✅. Тест-сьют: 685 passed, 9 skipped, 0 failed.
**Last Updated:** 2026-07-12
**Next Action:** Phase 7 (Voice mode).

### V5 Phase 6 — Certificates ✅ (2026-07-12)
- **Certificate** model + migration 0041; unique per (user, module); verification_code 24-char hex
- **POST /certificates/issue/{module_id}** — idempotent; requires 100% completion OR MCQ ≥ 70%
- **GET /certificates/my** — list all earned certs with LinkedIn share URL
- **GET /certificates/verify/{code}** — public, no auth; respects hide_name opt-out
- **GET /certificates/{id}/download** — PDF via reportlab (name, module, hours, score, verify link)
- **PATCH /certificates/{id}/hide-name** — toggle name visibility on public verify page
- **/verify/[code]** SSR page — green valid badge / red not-found; no auth required
- **Settings page**: "My Certificates" section — download, LinkedIn share, verify, hide-name toggle
- **Module page**: auto-issues cert when all lessons complete; shows banner with verify link
- 17 new tests in `test_v5_phase6.py`

### V5 Phase 5 — Spaced Repetition System ✅ (2026-07-12)
- **LessonSrsItem** + **LessonMcqCache** models; migration 0040
- **POST /srs/enqueue** — opt lesson or article into SM-2 queue (idempotent; honors `srs_enabled` preference)
- **GET /srs/queue** — due items with cached MCQs (AI-generated per lesson, shared across users)
- **POST /srs/review/{id}** — quality 0-5 → SM-2 updates interval/ease_factor/next_review_at
- **GET /srs/stats** — total_enrolled + due_today per user
- **DELETE /srs/items/{id}** — individual opt-out
- **Dashboard**: `srs_due` in base stats + today_plan; DailyGoalWidget now 3-col (flashcards · SRS lessons · goal)
- **/srs-review page**: MCQ quiz flow → quality rating → SM-2 scheduling; empty-state with CTA to modules
- **Lesson page**: "Reinforce?" prompt appears after marking lesson complete (calls enqueue, dismissable)
- 22 new tests in `test_v5_phase5.py`

### V5 Phase 4 — Social Learning ✅ (2026-07-12)
- **AssignmentStatus** model + migration 0039 (`assignment_statuses`, extended `comments`, `deck_collaborators`)
- **POST /courses/assignments/{id}/submit** — student self-submit (idempotent, enrollment-gated)
- **GET /courses/my-assignments-all** — student sees all pending assignments across classes
- **GET /courses/{id}/group-progress** — aggregate class progress (teacher + enrolled students)
- **GET /courses/{id}/progress-csv** — teacher-only CSV export (name, email, status, score, submitted_at)
- **Comment Q&A extensions**: comment_type, entity_id, parent_id, upvotes, accepted_answer_id
- **GET/POST /comments/module/{entity_id}** — Q&A with nested answers (questions sorted by upvotes)
- **POST /comments/module/{id}/upvote** — upvote question or comment
- **POST /comments/module/{qid}/accept/{aid}** — accept answer (author or teacher/admin)
- **GET /comments/module/{id}/ai-hint** — teacher gets AI draft from Claude Haiku (not auto-posted)
- **DeckCollaborator** model — add/list/remove co-editors on shared decks
- **Dashboard**: MyAssignments widget shows pending/overdue assignments to students
- 23 new tests in `test_v5_phase4.py` (20 pass, 3 skipped — deck collaborators need existing cards)
- **CRITICAL ORDERING FIXES**: `my-assignments-all` moved before `/{course_id}`; Q&A routes moved before `/{content_type}/{slug}`

### V5 Phase 3 — Point-of-Care Practice Mode ✅ (2026-07-11)
- **GET /practice/lab-values** — multi-species lab reference (human/dog/cat) from JSON data
- **GET /practice/algorithms** — list clinical algorithms with vet_only filter
- **GET /practice/algorithms/{slug}** — full algorithm with decision steps
- **GET /practice/search** — authenticated search across algorithms + modules
- 23 new tests in `test_v5_phase3.py`

### Phase 11 — Personal Exam Study Planner ✅ (2026-06-12)
- **Backend: `POST /student/exam-prep/plan`** — authenticated; accepts `exam_type` (usmle_step1/2/3, nclex_rn/pn, ukmla, plab, custom), `exam_date` (ISO), `daily_hours`; fetches all published modules + user progress; calls Claude Haiku to generate a week-by-week schedule; returns `{exam_label, days_remaining, total_weeks, weeks: [{theme, modules, daily_hours, milestone}], tip}`; cached 6h per user/exam/date combo
- **Settings page**: new "Exam Preparation" section with exam type dropdown + date picker; saves to `user.preferences.exam_type` + `user.preferences.exam_date`; shows "View My Study Plan →" button when both are set
- **Frontend: `/study-plan` page** — countdown (color-coded by urgency), study tip, week-by-week cards with theme/modules/milestone; "Regenerate" button; auto-generates on load if exam prefs already set; daily hours slider
- **`adaptivePlanApi.generateExamPlan()`** added to `frontend/lib/api.ts`
- 7 new tests in `test_v4_phase11.py` — 401 unauthenticated, past date 422, invalid date 422, returns plan with correct structure, all exam types, days_remaining accuracy

### Phase 10 — AI MCQ Generation from Lesson ✅ (2026-06-12)
- **Backend: `POST /ai/lessons/{lesson_id}/generate-quiz`** — authenticated; fetches lesson content, calls Claude Haiku with structured JSON prompt, returns 5 USMLE-style MCQ questions with options (A-D), correct answer, and explanation
- **`call_claude_structured()`** — new utility in `ai_router.py` for direct Claude calls with custom system prompts (structured output, bypasses standard routing)
- **`LESSON_MCQ_SYSTEM` + `lesson_mcq_prompt()`** — new prompt and template in `tutor_prompts.py`; supports easy/medium/hard difficulty
- **Frontend: `LessonQuizPanel` component** — `frontend/components/ui/LessonQuizPanel.tsx`; renders for authenticated users on lesson page; flow: idle (difficulty selector + generate button) → loading spinner → question-by-question quiz (progress bar, ABCD options, check answer, explanation) → score screen (X/5 correct, color-coded feedback); inserted above navigation footer in `modules/[id]/page.tsx`
- **`aiApi.generateLessonQuiz()`** added to `frontend/lib/api.ts`
- 6 new tests in `test_v4_phase10.py` — 401 unauthenticated, 404 unknown lesson, returns 5 questions, correct structure, difficulty param, invalid UUID

### Phase 9 — Clinical Calculators backend + Save Result ✅ (2026-06-12)
- **Backend: `GET /calculators`** — public catalog of 22 clinical calculators (slug, name, category, icon)
- **Backend: `POST /calculators/{slug}/save-result`** — authenticated; saves inputs/score/risk_level/note to `calculator_results` table
- **Backend: `GET /calculators/history`** — authenticated; returns user's saved results newest first, optional `?slug=` filter
- **Backend: `DELETE /calculators/history/{id}`** — authenticated; ownership-scoped delete
- **`CalculatorResult` model** — `calculator_results` table with JSONB inputs + 3 indexes; Alembic migration `2b5112c7bd74`
- **Frontend: `calculatorsApi`** — added to `frontend/lib/api.ts` (list, saveResult, getHistory, deleteResult)
- **Frontend: `SaveResultPanel`** — new component in `CalculatorWidget.tsx`; renders for authenticated users after calculation; optional note textarea; save/saved/error states; inserted after `AiPanel` in CheckboxCalc right panel
- 14 new tests in `test_v4_phase9.py` — public catalog, 401 unauthenticated, save/note/unknown-slug, history/filter/scoping, delete/wrong-user/invalid-uuid

### V3 Phase 8 — Mobile App (React Native Expo) ✅ (2026-06-12)
- **WatermelonDB offline sync** (pre-existing): `syncModules()`, `syncFlashcards()`, `pushPendingReviews()` in `mobile/src/lib/database.ts`; schema: modules, lessons, flashcards, ai_messages tables
- **Push notifications** (pre-existing): `registerForPushNotifications()`, `scheduleFlashcardReminder()`, `setupNotificationResponseHandler()` in `mobile/src/lib/notifications.ts`; daily 9:00 AM reminder if due cards > 0
- **Offline AI fallback** (pre-existing): keyword matching (MI, HTN, sepsis, diabetes, antibiotics) + offline queue in `offlineAI.ts`
- **8 existing screens** (pre-existing): dashboard (XP/streak), modules, flashcards, AI tutor, leaderboard, achievements, auth/login, auth/register
- **NEW: `mobile/app/module/[id].tsx`** — module detail screen: lesson list sorted by lesson_order, taps navigate to lesson reader, shows lesson count + estimated time
- **NEW: `mobile/app/lesson/[id].tsx`** — lesson reader: renders all content block types (h1/h2/h3/p/list/callout/warning/table), medical disclaimer, clinical risk badge, lay summary section, "Mark as complete" button → `POST /progress/lesson/{id}/complete`
- **NEW: modules.tsx** — module cards now tap to navigate to `/module/{id}` (Expo Router)
- **Backend: `PATCH /auth/push-token`** — stores Expo push token on the authenticated user; empty/whitespace → 400
- **Backend: `push_token` column** added to `users` table + Alembic migration `afb63dd2fe0d`
- 6 new tests in `test_v4_phase8.py` — 401 without auth, token stored, empty 400, whitespace 400, idempotent update, user-scoped isolation

### V3 Phase 7 — PWA + i18n foundation ✅ (2026-06-12)
- `frontend/public/manifest.json` — full Web App Manifest: name, icons, shortcuts (AI Tutor, Modules, Flashcards), screenshots, theme/bg colors matching design system
- `<link rel="manifest">` added to `app/layout.tsx` — browsers can now prompt PWA install
- **Already in place (pre-existing):** `sw.js` (cache-first shell + stale-while-revalidate assets + lesson offline cache), `icon-192.png` + `icon-512.png`, all PWA meta tags (theme-color, apple-mobile-web-app-capable, etc.), `PWAInstallPrompt.tsx` (30s delayed prompt, respects dismissal), `/offline` page, i18n system (7 languages, lazy loading, RTL for Arabic, dot-notation keys), `Module.language` field + `?language=` API filter
- 8 new tests in `test_v4_phase7.py` — language field defaults, language filter API (en/ru/unknown), specialty module filter, public endpoint access
- Acceptance criteria met: PWA installable (manifest + sw + icons + HTTPS on prod); en/ru switching without page reload via existing Zustand i18n context

### V4 Phase 6 — Reviewer workspace ✅ (2026-06-12)
- RBAC: `reviewer` role added to `require_reviewer()` dep in `app/api/deps.py`
- Reviewer queue API (5 endpoints in `admin.py`):
  - `GET /api/v1/admin/reviewer-queue` — paginated, sorted by view_count desc, only `verification_status=passed`
  - `GET /api/v1/admin/reviewer-queue/{id}` — full detail with body/sources/faq/verification_report
  - `POST /api/v1/admin/reviewer-queue/{id}/approve` → `verification_status=human_reviewed`, sets `reviewed_by`
  - `POST /api/v1/admin/reviewer-queue/{id}/request-changes` → `verification_status=failed` + `review_note`
  - `GET /api/v1/admin/reviewer-queue/stats/summary` — queue_depth, unresolved_feedback, human_reviewed_total
- Weekly digest: `_weekly_reviewer_digest()` + Monday 08:00 UTC cron job in `scheduler.py`
- Email: `send_reviewer_digest()` in `email_service.py` — HTML digest with 2 stat cards
- Frontend: `app/(app)/admin/reviewer/page.tsx` — full reviewer queue UI (list + detail panel + approve/reject modal)
- Article page: `human_reviewed` status now shows "Reviewed by Specialist" badge with reviewer name + date
- Article disclaimer: `human_reviewed` styled as green (same as `expert_verified`)
- 14 new tests in `test_v4_phase6.py` — all passing in full suite (450 total)

### V4 Phase 5 — Localized landings + hreflang audit ✅ (2026-06-12)
- `app/[locale]/page.tsx` — 6 locale routes (/ru, /de, /fr, /es, /tr, /ar); /en redirects to /
- LandingPage: `initialLocale` prop + `dir="rtl"` for Arabic
- Sitemap: each non-en sitemap now includes the /{locale} landing page entry
- `scripts/ops/seo_audit.py` — checks 200 status, canonical, hreflang reciprocity, disclaimer presence
- CI: `seo-audit` job (allowed-to-fail) runs on push to main against prod

### V4 Phase 4 — New landing: two-audience bifurcation ✅ (2026-06-12)
- Hero redesigned: two-card bifurcation (professionals → /register, patients → /learn)
- Real API stats counter: `GET /api/v1/public/stats` returns verified articles, modules, languages
- Search bar: plain-language search field → `/articles?search=...` (no auth, no AI calls)
- MiniQuiz component (`components/ui/MiniQuiz.tsx`): 3-question interactive quiz, loads from real public quiz API
- Content pipeline block: 4 steps (sources → AI → verification → human review) + live counters + editorial link
- "For specialists" block: feature list + pricing preview cards → /pricing
- Footer updated: trust links (/about, /editorial-policy, /medical-disclaimer, /contact) + disclaimer line
- i18n: 41 new keys added to all 7 locales (en/ru fully translated, others English fallback)
- page.tsx now server-fetches stats + mini-quiz data (parallel fetch, no client waterfall)

### V4 Phase 3 — Trust pages & E-E-A-T ✅ (2026-06-12)
- Static trust pages (SSR, multilingual 7 langs): `/about`, `/editorial-policy`, `/medical-disclaimer`, `/contact`
- `frontend/components/layout/PublicFooter.tsx` — shared footer with trust links + disclaimer line
- `frontend/lib/trust-i18n.ts` — server-safe SSR translation library for trust pages (7 languages)
- `frontend/app/reviewers/[slug]/page.tsx` — reviewer profile scaffold with Schema.org Person
- Schema.org enhanced on article pages: `dateModified`, `lastReviewed`, `reviewedBy`, `citation` from verified sources
- Backend: `Reviewer` model + alembic migration 0034 + `/api/v1/reviewers` endpoint (list + detail)
- Article detail response now includes `reviewed_by` and `updated_at` fields
- Sitemap: 4 trust pages added to static pages list in `sitemap-builder.ts`
- 9 new tests in `test_v4_phase3.py` — all passing

### V4 Phase 2 — Translation QA ✅ (2026-06-12)
- Medical glossary: 250 canonical terms × 7 languages in `backend/app/data/med_glossary/{en,ru,de,fr,es,tr,ar}.json`
- `check_translation_quality()` in `content_verifier.py`:
  - Number/unit corruption check (regex, digit-level comparison)
  - Negation preservation check (Haiku semantic check)
  - Glossary canonical term check (stem matching for declined forms)
  - Returns `passed | failed` + structured report
- `ArticleTranslation.translation_verification_status` + `translation_qa_report` + `translation_qa_checked_at`
- Alembic migration 0033: adds QA fields to `article_translations`
- Article detail endpoint: `translation_verification_status=failed` → fallback to English + `translation_under_review: true` marker
- `_translate_article()` updated to run QA after translation, stores qa_status/qa_report in DB
- Glossary hints injected into translation prompts via `_build_glossary_prompt_context()`
- `backend/app/scripts/back_translate_check.py` — 5% random sampling back-translation spot-check
- 18 new tests in `test_v4_phase2.py` — all passing

### V4 Phase 1 — Content Verification Pipeline ✅ (2026-06-12)
- Alembic migration 0032: verification fields on articles/news_articles, content_feedback table
- Model updates: Article.verification_status → V4 enum (pending/passed/failed/human_reviewed); ContentFeedback model added
- `backend/app/services/content_verifier.py` — claim extractor + source checker (Haiku-based)
- Publication gateway: all public article/news endpoints + sitemap filter out pending/failed
- `POST /api/v1/articles/feedback` — public content error reporting endpoint
- 22 new tests in `test_v4_phase1.py` — all passing
- i18n: 100+ hardcoded strings extracted to translation keys across 7 locales (dashboard, settings, nav)

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
- JWT_SECRET_KEY=<generate with: openssl rand -hex 32>  ← set in backend/.env, never commit
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

## 🗺 Roadmap V3 Progress

| Фаза | Название | Статус |
|------|----------|--------|
| Phase 0 | Подготовка репозитория | ✅ 2026-06-11 |
| Phase 1 | lay_summary (двухуровневый контент) | ✅ 2026-06-11 |
| Phase 2 | Режим «Пациент» (AI guardrails) | ✅ 2026-06-11 |
| Phase 3 | Публичный SEO-контур | ✅ 2026-06-11 |
| Phase 4 | Публичные квизы + шеринг | ✅ 2026-06-11 |
| Phase 5 | Геймификация (XP, стрики, лидерборд) | ✅ 2026-06-11 |
| Phase 6 | Контур «Владельцы животных» | ✅ 2026-06-11 |
| Phase 7 | PWA + i18n фундамент | ✅ 2026-06-11 |

Детали каждой фазы: `docs/MEDMIND_ROADMAP_V3.md`

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
