# MedMind AI — Development Plan

> Complete roadmap from zero to production-ready MVP.

---

## Project Summary
**MedMind AI** — global medical & veterinary education platform.  
Stack: FastAPI + PostgreSQL/pgvector + Redis + Claude API + Next.js 14 + React Native  
70 JSON modules already created. Build the platform around them.

---

## Phase 1: Infrastructure (Week 1–2) ✅
**Goal:** Running database, importable modules, working API skeleton

### Steps:
1. `docker-compose.yml` — PostgreSQL 15 + pgvector + Redis 7
2. Full database schema (18 tables)
3. FastAPI app skeleton with health check
4. SQLAlchemy 2.0 async models
5. Alembic migrations
6. **Module import script** — reads 70 JSON files → populates DB
7. Basic CRUD endpoints to verify data

### Success Criteria:
- `GET /api/v1/specialties` returns 7+ specialties
- `GET /api/v1/modules/CARDIO-001` returns full module data
- `GET /api/v1/modules/CARDIO-001/flashcards` returns flashcards

---

## Phase 2: Auth & User Management (Week 2–3)
**Goal:** Users can register, login, have roles and subscription tiers

### Steps:
1. JWT auth (register/login/refresh/logout)
2. User model with subscription_tier
3. Rate limiting middleware (AI requests/day by tier)
4. OAuth2 Google/Apple (optional for MVP)
5. Onboarding endpoint — 5-step wizard → Welcome Plan via Claude

### Success Criteria:
- Register, login, get JWT, make authenticated request
- Free user gets 403 on Pro content

---

## Phase 3: Core Learning API (Week 3–4)
**Goal:** Full content delivery + progress tracking + SM-2

### Steps:
1. All content endpoints (specialties, modules, lessons, flashcards, MCQ, cases)
2. Access control by subscription tier
3. SM-2 algorithm for flashcard spaced repetition
4. Progress endpoints (complete lesson, review flashcard, answer MCQ)
5. XP system + achievements
6. Streak tracking

### Success Criteria:
- User can complete a lesson, review flashcards with SM-2, answer MCQ
- XP is awarded correctly

---

## Phase 4: AI Tutor (Week 4–5)
**Goal:** Smart AI responses using Claude API with PubMed integration

### Steps:
1. AI request router (`services/ai_router.py`)
   - Free → Ollama / rejection
   - Simple → Claude Haiku
   - Complex → Claude Sonnet
2. Redis cache for AI responses (TTL 24h)
3. PubMed search proxy with Redis cache (TTL 7 days)
4. All system prompts (tutor, socratic, case, exam)
5. Streaming SSE responses
6. Conversation history storage

### Success Criteria:
- AI response with PubMed refs in <5s
- Cache hit returns instantly
- Rate limit blocks at correct thresholds

---

## Phase 5: Frontend (Week 5–8)
**Goal:** Fully functional web app matching the HTML prototype design

### Design Reference: `medmind-v2.html`
Colors: `--ink:#1a1814`, `--red:#c0392b`, `--bg:#f0ede8`  
Fonts: Syne (headings), Source Serif 4 (body)

### Core Pages:
1. **Landing** — hero, features, pricing
2. **Auth** — login, register, 5-step onboarding
3. **Dashboard** — role-based, today's tasks, streak, XP
4. **Modules** — specialty grid → module list → lesson reader
5. **Flashcards** — due cards, flip animation, SM-2 rating
6. **AI Tutor** — chat interface, mode selector, PubMed panel
7. **Cases** — clinical case viewer with AI discussion
8. **Progress** — charts, weaknesses, achievements
9. **Settings** — profile, notifications, subscription

### Key UX Principles:
- Dark sidebar (like HTML prototype)
- Single-page feel (no full reloads in study mode)
- Mobile-responsive from day 1

---

## Phase 6: Payments (Week 7–8)
**Goal:** Stripe subscriptions working

### Steps:
1. Stripe products: Student $15, Pro $40, Clinic $199, Lifetime $299
2. Checkout flow
3. Webhook: subscription.created → update user.subscription_tier
4. Pricing page

---

## Phase 7: Veterinary Mode (Week 8–9)
**Goal:** Vet-specific features

### Steps:
1. Species-specific dosing API
2. Vet toggle in user settings
3. VET module content (needs creation — 16 modules)
4. Drug safety by species

---

## Phase 8: Mobile App (Week 9–12)
**Goal:** iOS + Android app with offline support

### Steps:
1. React Native Expo scaffold
2. WatermelonDB for offline sync
3. Core screens mirroring web app
4. Push notifications for review reminders

---

## Improvement Ideas (Beyond TZ)

1. **Progress analytics dashboard** — weekly/monthly charts, accuracy trends
2. **Peer study groups** — compare progress with colleagues
3. **AI-generated exam simulations** — full USMLE-style mock exams
4. **Voice interaction** — ask questions by voice (Web Speech API)
5. **Smart notifications** — "You have 5 flashcards due today" push alerts
6. **Content versioning** — track guideline updates, notify users
7. **Teacher mode** — professors assign modules to students, track their progress
8. **PDF export** — generate study summaries and certificates
9. **Adaptive difficulty** — AI adjusts question difficulty based on performance
10. **Multilingual** — Russian/English toggle (content already bilingual in modules)

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Claude API costs exceed budget | Medium | High | Aggressive caching + Haiku routing |
| pgvector slow on large dataset | Low | Medium | Proper indexing + HNSW |
| Module JSON parsing errors | Low | Medium | Robust import script with error recovery |
| GDPR non-compliance | Medium | High | Email encryption, consent flow, data export |
| Stripe webhook missed | Low | High | idempotency keys, webhook retry handling |
