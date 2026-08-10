# MedMind AI — Project State (Session Recovery File)

> **CRITICAL**: Read this file first at the start of EVERY new session to restore context.
> Updated every time meaningful work is done.

---

## 🟢 Current Status
**Phase:** Gulf Pipeline — банки заполнены, образовательный контент создан, LLM re-audit завершён ✅
**Last Updated:** 2026-08-10
**Next Action:** Назначить local reviewer (`python -m app.scripts.assign_reviewer --email ... --jurisdictions sa`); подтвердить source_url для 77 jurisdiction_rules; дождаться завершения переводов (~3227 lesson translations pending)

**Completed 2026-08-10 (latest session):**
- `/learn/modules/[code]` — публичные SSR-страницы для Gulf модулей (SEO, schema.org Course, paywall после первого урока)
- `GET /modules/{code}/public` — бэкенд эндпоинт для публичного просмотра модулей
- `GET /exam/gulf-modules-sitemap` — эндпоинт для sitemap
- Sitemap builder обновлён — Gulf модули добавлены (priority 0.8)
- ExamLandingTemplate — блок "Study Materials" для Gulf страниц экзаменов
- Kuwait (moh_kw): добавлены режимы `moh_kw_practice` (40Q/60min) и `moh_kw_full` (100Q/180min) в бэкенд EXAM_MODES и фронтенд GULF_MODE_IDS/GULF_EXAM_SLUGS/GULF_EXAM_INFO
- Gulf analytics bug fix: фильтр `mode_id.like("gulf_%")` → `mode_id.in_(gulf_mode_ids)` (все сессии пользователей теперь корректно отображаются)
- Gulf analytics bug fix: парсинг exam_slug (`mode_parts[1]` → `mode_to_slug` dict lookup)
- Readiness endpoint: `valid_slugs` добавлен `moh_kw`
- `generate_lay_summaries.py`: исправлено `Module.module_code` → `Module.code`, `settings.anthropic_api_key` → `settings.ANTHROPIC_API_KEY`, `settings.database_url` → `settings.DATABASE_URL`
- Lay summaries: скрипт `generate_lay_summaries.py` исправлен (Module.code, ANTHROPIC_API_KEY, DATABASE_URL). Запуск пока не возможен — нет баланса Anthropic API. После пополнения: `docker exec medmind_backend bash -c "for code in CULT-GULF-001 PHARM-GULF-001 REG-AE-001 REG-BH-001 REG-CLIN-001 REG-HAAD-001 REG-KW-001 REG-MOHUAE-001 REG-OM-001 REG-QA-001 REG-SA-001; do python3 -m app.scripts.generate_lay_summaries --module-code \$code; done"`

---

### BANK-SCALE — Масштабирование банка вопросов ✅ (2026-07-30)

**Spec:** `docs/BANK_SCALE_SPEC.md`
**Total tests:** 70 (B1: 15 + B2: 15 + B3: 12 + B4: 14 + B5: 14), все проходят

**Bank scale table** (updated 2026-08-10):
| Exam | Questions | Target | Status | Human reviewed |
|------|-----------|--------|--------|----------------|
| SNLE | 820 | 600 | ✅ 137% | 0 |
| DHA | 584 | 450 | ✅ 130% | 0 |
| QCHP | 317 | 300 | ✅ 106% | 0 |
| OMSB | 317 | 300 | ✅ 106% | 0 |
| NHRA | 317 | 300 | ✅ 106% | 0 |
| MOHUAE | 317 | 300 | ✅ 106% | 0 |
| HAAD | 317 | 300 | ✅ 106% | 0 |
| Total active | 2309 | — | 0 quarantined | 0 human reviewed |

**Final bank state (2026-08-10):**
- total active: 2309 | ai_verified: 2309 (100%) | pending reverify: 0
- Arabic rationales: 2153/2309 (93.3%) | 156 pending (cron auto-running every 30 min)
- Quarantined (jurisdiction_sensitive=true AND jurisdiction_verified_for IS NULL): **0** ✅ (LLM re-audit cleared all)
- All pending AI verifications: **0** ✅ (all cleared)

**LLM Re-audit results (2026-08-08):**
- 42 quarantined → 0 genuinely quarantined after semantic re-audit
- 3 initially confirmed sensitive (HIPAA, 911, US child abuse immunity) were subsequently cleared or retired
- `reaudit_quarantined.py` is available for re-runs after new question generation

**To run when Groq resets:**
```bash
docker exec medmind_backend python3 -m app.scripts.translate_rationales_ar  # 156 remaining Arabic
```

**Generation pipeline fixes (2026-08-07):**
- `_count_existing_db` → JSONB type_coerce containment (not module-based)
- Cerebras model: `gpt-oss-120b` → `gemma-4-31b` (reasoning model returned no content)
- `max_tokens` per batch: `batch × 700, min 4096` (was 3000 → JSON truncation)
- `max_wait` 90s → 300s (handles 120s Cerebras rate-limit rotation)
- `_mcq_db_writer.py`: now saves `origin`, `jurisdiction_sensitive`, `jurisdiction_verified_for`

#### B1 — Content Source Registry ✅ (2026-07-29)
- `ContentSource` model + migration `w9x0y1z2a3b4`
- 10 sources seeded с вручную проверенными лицензиями:
  - **text_reuse_allowed=True**: CDC (public domain US gov), MedlinePlus Health Topics (public domain US gov)
  - **text_reuse_allowed=False**: StatPearls (CC BY-NC-ND 4.0), WHO, NICE, NCSBN, SCFHS/SNLE, DHA, QCHP, MedlinePlus A.D.A.M.
- `GET /api/v1/public/content-sources` — публичный endpoint
- Публичная SSR-страница `/content-sources`, `ContentAttribution` компонент, sitemap

#### B2 — Open Source Corpus Ingestion + Generation ✅ (2026-07-30)
- `SourceDocument` model + migration `x0y1z2a3b4c5` (SHA-256 dedup)
- `ingest_open_sources.py`: MedlinePlus + CDC (public domain) + StatPearls (facts only, CC BY-NC-ND)
- `question_claim_check.py`: Groq-based extract-claims → check-vs-source → reject if contradicted
- `generate_from_source_docs.py`: генератор NCLEX MCQ с claim-верификацией, `GENERATION_PROMPT_VERSION="b2-v1"`
- Реальный ingest: 15 документов (pharmacological=4, safe_effective_care=9, physiological_adaptation=2)
- Ключи Groq: KEY_3/KEY_4/KEY_MODULE_2/KEY_CASES — только для пайплайна генерации контента

#### B3 — Gap Analysis Coverage ✅ (2026-07-30)
- `GenerationQueue` model + migration `y1z2a3b4c5d6`
- `GET /admin/bank-coverage`: покрытие по exam × category × type vs blueprint-таргеты
- `GET /admin/bank-coverage/queue`: список заданий с фильтрами
- `plan_generation.py`: вычисляет дефициты и заполняет generation_queue
- Blueprint веса: NCSBN NCLEX-RN 2023 (только публичные категории, текст не копировался)
- Volume targets: NCLEX-RN 2000, SNLE 1200, DHA 900, Gulf exams 500

#### B4 — Reviewer Workplace ✅ (2026-07-30)
- `QuestionReview` model + migration `z2a3b4c5d6e7` (рубрика 7 измерений 1-5)
- `GET /reviewer/queue`: следующий вопрос приоритизирован: flagged→health!=ok→pending→follow_ups
- `POST /reviewer/submit/{id}`: approve → `human_reviewed`; reject → retired + GenerationQueue entry
- `GET /reviewer/stats`: личная статистика рецензента
- `GET /admin/review-insights`: агрегаты по рубрике, reject reasons, комментарии для Groq-кластеризации

#### B5 — Freemium Layout ✅ (2026-07-30)
- `FREEMIUM_CONFIG` в `app/core/freemium.py` — единый источник правды (не в коде компонентов)
- Анонимный лимит: 20 вопросов/день (по IP-хешу, Redis, TTL 25ч)
- `GET /public/practice/free`: анонимная практика с paywall при исчерпании лимита
- `GET /public/practice/free/status`: текущее использование/остаток
- `GET /public/freemium/config`: публичный конфиг для UI пейволла
- `paywall_hit`, `anon_limit_hit`, `free_practice` события в аналитику
- B5 feature flags в `feature_flags.py` DEFAULTS

---

### V7 Roadmap — Bank Health + Psychometrics ✅ (2026-07-29)

| Фаза | Название | Статус | Коммит |
|------|----------|--------|--------|
| Phase 1 | Психометрика вопросов | ✅ | feat(v7-phase-1) |
| Phase 2 | Дашборд здоровья банка | ✅ | feat(v7-phase-2) |
| Phase 3 | Пост-экзаменационная петля | ✅ | feat(v7-phase-3) |
| Phase 4 | Вопрос ↔ AI-тьютор (follow-up chips) | ✅ | feat(v7-phase-4) |
| Phase 5 | Сравнение с сообществом | ✅ | feat(v7-phase-5) |
| Phase 6 | Разбор mock-экзамена | ✅ | feat(v7-phase-6) |

**Tests:** 72/72 passed (all V7 tests green in full suite)

#### Phase 1 — Psychometrics
- `QuestionStats` model (p_value, discrimination, attempt_count, health)
- `QuestionAttempt` model (per-user attempt log for discrimination calculation)
- Alembic migration `t6u7v8w9x0y1`: `question_stats`, `question_attempts` tables
- `psychometrics.py` service: p-value (proportion correct), discrimination (biserial), health classification
- Nightly cron job: recalculates stats for all questions answered ≥40 times
- Health labels: excellent / good / weak / key_suspect (flagged for review)
- 10 tests: unit (p-value, discrimination, health thresholds) + HTTP (auth, snapshot, recalc)

#### Phase 2 — Bank Health Dashboard
- Admin endpoint `GET /exam/admin/bank-health` — distribution by health label + calibration stats
- `ContentAuditLog` model: tracks all psychometric recalculations with before/after health
- `MCQQuestion.status` field: draft / active / suspended / retired (lifecycle management)
- Admin UI tab "Bank Health" in `/admin` page: health distribution bars, calibration chart
- 12 tests (3 unit, 9 HTTP)

#### Phase 3 — Post-Exam Survey Loop
- `ExamOutcome` model + migration `v8w9x0y1z2a3`: tracks real exam results after NCLEX
- Cron: `_readiness_snapshot_job` (22:00 UTC) — creates ExamOutcome rows for users whose exam is tomorrow
- Cron: `_survey_reminder_job` (10:00 UTC) — sends survey emails at T+2d and T+7d
- Cron: `_community_percentile_job` (03:00 UTC) — computes per-user category accuracy, caches in Redis
- REST API: GET /exam-outcomes/pending, POST /exam-outcomes/{id}/submit, POST /exam-outcomes/{id}/unsubscribe
- Admin: GET /admin/readiness-validation (correlation report), GET /admin/blueprint-calibration
- Frontend: 3-step survey page `/survey/exam-outcome/[id]`, `ExamSurveyBanner` on dashboard
- 10 tests

#### Phase 4 — Follow-up Chips (Question ↔ AI Tutor)
- `POST /exam/questions/{id}/followup` — 5 chip types: why_wrong, memory_tip, concept_review, clinical_apply, mnemonics
- `question_followup.py` prompt service — builds (system_prompt, user_message) tuple per chip
- AI quota enforced via `check_ai_rate_limit`; `follow_up_count` incremented; health escalated to `key_suspect` at threshold
- Frontend: follow-up chip buttons appear after initial explanation in exam review mode
- 7 tests

#### Phase 5 — Community Comparison
- `GET /exam/questions/{id}/community` — pass rate with strict privacy guard (sample_size_ok=True only when group ≥30)
- `GET /exam/nclex/community-percentile` — user percentile rank vs all users (cached Redis, 26h TTL)
- `CommunityPassRate` component in exam page — "N% get this right ← challenging" label
- 6 tests

#### Phase 6 — Mock Exam Debrief
- `mock_debrief.py`: 7 rule-based pattern detectors (ordered_errors, calculation_errors, sata_errors, pharmacology_errors, priority_keyword_errors, infection_control_errors, slow_question_pattern)
- `run_detectors(per_question)` — fires detectors, returns list of patterns with descriptions
- `analyze_timing(per_question)` — avg/total time, slow questions, would_exceed_time_limit
- `GET /exam/sessions/{id}/mock-debrief` — aggregates patterns + timing + category breakdown
- `GET /exam/sessions/{id}/mock-debrief/pdf` — reportlab PDF export (name, score, patterns, category table)
- `MockDebriefPanel` frontend component — expandable panel with patterns (amber alerts), timing stats, category breakdown, PDF download
- 10 tests

---

### Mobile UX Polish + SEO + i18n ✅ (2026-07-23)
- **Inline MCQ quiz in lesson screen**: after completing a lesson, users tap "Practice Quiz" to get a random MCQ from that module. Answer submitted to progress API (XP awarded, SM-2 tracked), explanation shown on reveal. Next question button cycles through more.
- **Standalone mobile quiz screen** (`/quiz`): pick specialty → 10 shuffled MCQs from modules → answer with reveal → score screen. Connected from dashboard "Quick Quiz" quick action.
- **Mobile dashboard avatar + logout**: tapping user initial shows native Alert with Sign Out (calls logout() + redirects to /auth/login)
- **Mobile progress screen**: stats grid (lessons/cards/MCQs/accuracy), 14-day activity chart, weekly quiz accuracy chart (colour-coded green/amber/red)
- **Nav fixes**: Sidebar + MobileNav "Calc History" link corrected to /calculator-history (was /calculators)
- **SEO**: /articles, /calculators, /drugs, /news, /learn and sub-pages, /quiz/public, /nclex, /bots — all added to sitemap
- **i18n**: exam submit_confirm_title/body/cancel + retry_wrong + print_results translated in AR/ES/FR/TR/DE (were English placeholders)
- **TypeScript**: 0 errors on full frontend check
- **Tests**: 911 passed, 9 skipped, 0 failed ✅

### Performance Analytics ✅ (2026-07-22)
- **Weekly Quiz Accuracy trend**: `GET /progress/quiz/weekly-trend` — 8-week bar chart on progress page
- **NCLEX Readiness mini-card** on dashboard — colored score circle + exam countdown
- **Quiz performance by specialty** — `GET /progress/quiz/performance` — horizontal bars
- Tests: 906 passed, 9 skipped (full suite)

### Jurisdictions — Phase L1 ✅ (2026-08-06)
| Profile | Regulator | Norms verified | Norms needs_human | In quarantine | Confirmed local | Launch readiness |
|---------|-----------|---------------|-------------------|---------------|-----------------|-----------------|
| sa | SCFHS | 0 | 11 | 0 | 0 | 0/10 |
| ae_dubai | DHA | 0 | 10 | 0 | 0 | 0/10 |
| ae_abudhabi | DOH | 0 | 10 | 0 | 0 | 0/10 |
| qa | QCHP | 0 | 10 | 0 | 0 | 0/10 |
| om | OMSB/MOH | 0 | 10 | 0 | 0 | 0/10 |
| bh | NHRA | 0 | 10 | 0 | 0 | 0/10 |
| ae_moh | MOHAP | 0 | — | 0 | 0 | 0/10 |
| kw | MOH-KW | 0 | 6 | 0 | 0 | 0/10 |

*All 77 rules status=needs_human. Total quarantined: 0 (LLM re-audit cleared all on 2026-08-08).
DB tables: `jurisdiction_profiles`, `jurisdiction_rules`. Admin: `/admin/jurisdictions`. Seed: `app/scripts/seed_jurisdiction_profiles.py`.*

**Gulf educational modules (11 total, 2026-08-10):**
| Module | Jurisdiction | Lessons | Arabic |
|--------|-------------|---------|--------|
| REG-SA-001 | Saudi Arabia (SCFHS) | 3 | queued |
| REG-AE-001 | UAE DHA/DOH dual | 2 | queued |
| REG-QA-001 | Qatar (QCHP) | 3 | ✅ done |
| REG-OM-001 | Oman (OMSB) | 3 | ✅ done |
| REG-BH-001 | Bahrain (NHRA) | 3 | ✅ done |
| REG-MOHUAE-001 | UAE Northern Emirates (MOHAP) | 2 | ✅ done |
| REG-KW-001 | Kuwait (MOH-KW) | 3 | pending import |
| PHARM-GULF-001 | All Gulf | 4 | ✅ done |
| CULT-GULF-001 | All Gulf (cultural) | 4 | queued |
| REG-CLIN-001 | All Gulf (clinical) | 3 | queued |

**Study-modules API:** `GET /exam/study-modules/{slug}` — returns modules for exam slug via JSONB containment
**Assign reviewer CLI:** `python -m app.scripts.assign_reviewer --email user@example.com --jurisdictions sa`

**L2 — Audit & Quarantine ✅ (2026-08-06, updated 2026-08-10)**
- `mcq_questions`: added `jurisdiction_sensitive`, `jurisdiction_verified_for`, `origin`, `jurisdiction_audit_at`, `jurisdiction_audit_notes` (migration b2c3d4e5f6a7)
- Initial audit: 205 Gulf questions → 44 flagged (21%), quarantined
- LLM re-audit (2026-08-08): `reaudit_quarantined.py` cleared all 44 → **0 quarantined** (all were universal medicine)
- Quarantine enforced in exam.py query layer (L2.3)
- `map_gulf_questions.py` blocks re-mapping sensitive questions (L2.4)
- Admin report: `GET /admin/jurisdiction-audit`
- Classifier: `app/scripts/audit_jurisdiction_sensitivity.py` (re-run after question edits)
- 205 questions tagged `origin='nclex_mapped'`
- **L6 — Launch Readiness Gate ✅ (2026-08-06)**
- `GET /admin/launch-readiness?exam=snle` — 10-point checklist:
  1. blueprint_verified_at < 12 months
  2. blueprint_source is official URL
  3. active questions >= target (snle=600, dha=450, others=300)
  4. no quarantined questions in active pool
  5. >= 150 human_reviewed questions with avg realism >= 4.0
  6. 100% jurisdiction-sensitive questions locally confirmed
  7. 2 mocks assemblable (total >= 2x mock_size)
  8. Arabic rationales >= 95%
  9. non-affiliation disclaimer present in exam_definitions
  10. marketing_ready is currently false (gate active, confirm before enabling)
- `PATCH /admin/exams/{slug}/marketing-ready` — sets flag; blocked if any quarantined questions remain
- `marketing_ready` returned in exam definitions API response (`_exam_def_to_dict`)
- Frontend: `/exams/[slug]/page.tsx` — `robots: {index: false, follow: true}` when `marketing_ready=false`; `ExamDefinition` interface extended with `marketing_ready?: boolean`
- All 7 Gulf exam landings currently noindex (marketing_ready=false in DB)

**L5 — Local Reviewer Gate ✅ (2026-08-06)**
- Reviewer model: added `jurisdictions` (JSONB), `license_country`, `license_number` (migration d4e5f6a7b8c9)
- QuestionReview model: added `locally_correct`, `scope_ok`, `culturally_appropriate`, `local_note`, `jurisdiction_slug`
- API: `GET /reviewer/queue/jurisdiction?jurisdiction=sa` — returns quarantined questions for authorized reviewers
- API: `POST /reviewer/submit-jurisdiction/{id}` — locally_correct=yes+scope_ok=yes → exits quarantine; no → retired+regen; local_note → draft JurisdictionRule (needs_human)
- Gate enforced: jurisdiction_verified_for only set by authorized human reviewer via API
- L5.5: local_note auto-creates draft JurisdictionRule for later source confirmation

**L4 — Blueprint Weights & Regional Content ✅ (2026-08-06)**
- Blueprint already verified in exam_registry.py: SNLE from SCFHS Guide 2024 (2026-07-30), all others (2026-07-20)
- Target volumes lowered per spec: SNLE=600, DHA=450, others=300 (in `EXAM_TARGETS` dict in generate_gulf_questions.py)
- `marketing_ready` field added to `exam_definitions` (migration c3d4e5f6a7b8); all exams default false
- 11 Gulf educational modules (33 lessons total, as of 2026-08-10):
  - REG-SA-001: SCFHS scope, consent, MERS-CoV, medication safety (3 lessons)
  - REG-AE-001: DHA/DOH dual structure, incident reporting, patient rights (2 lessons)
  - REG-QA-001: QCHP, Qatar, HMC context (3 lessons) ✅ imported + Arabic
  - REG-OM-001: OMSB, Oman, Brucellosis (3 lessons) ✅ imported + Arabic
  - REG-BH-001: NHRA, Bahrain, cultural care (3 lessons) ✅ imported + Arabic
  - REG-MOHUAE-001: MOHAP UAE Northern Emirates (2 lessons) ✅ imported + Arabic
  - REG-KW-001: MOH-KW Kuwait (3 lessons) — created 2026-08-10, import pending
  - PHARM-GULF-001: INN names, SI units, high-alert meds, psychotropics (4 lessons) ✅ imported + Arabic
  - CULT-GULF-001: gender privacy, Ramadan, gelatin/ethanol, prayer/EOL (4 lessons)
  - REG-CLIN-001: heat stroke management, MERS-CoV, emergency numbers, Hajj health (3 lessons)
- L4.5 Arabic translation: 27 lessons translated immediately; remainder via `_retry_pending_lesson_translations_job`

**L3 — Locale-Aware Generator ✅ (2026-08-06)**
- `prompts/jurisdiction_context.py`: builds JurisdictionContext from DB (verified rules only); formats prompt block with mandatory constraints + deficit domains
- `services/locale_linter.py`: post-generation linter with 5 rule classes (us_911, us_regulatory, us_agency, non_si_units, us_brand_drug); returns LintResult; failed questions discarded
- `generate_gulf_questions.py`: fetches jurisdiction context per exam slug; applies linter after generation; sets origin='gulf_native' on new questions; jurisdiction_verified_for=None (stays quarantined until L5)
- Linter test: bad question with HIPAA/911/Narcan/mg/dL/CDC → 5 violations; good question (mmol/L/°C/paracetamol) → passes
- Currently all rules are needs_human → prompt carries mandatory constraints only; verified norms will auto-appear once human reviewers confirm sources

### Exams Registry — Gulf (G1) ✅ (2026-07-20, updated 2026-08-10)
| Exam | Bank (Q) | Status | Blueprint verified |
|------|----------|--------|--------------------|
| SNLE (Saudi Arabia) | shared | active | ✅ |
| DHA (Dubai UAE) | shared | active | ✅ |
| QCHP (Qatar) | shared | active | ✅ |
| OMSB (Oman) | shared | active | ✅ |
| NHRA (Bahrain) | shared | active | ✅ |
| MOH UAE (N. Emirates) | shared | active | ✅ |
| DOH/HAAD (Abu Dhabi) | shared | active | ✅ |
| MOH Kuwait (moh_kw) | 300 Q | active | ✅ |
*Questions shared from NCLEX bank via map_gulf_questions.py. All 8 exams confirmed status='active' in DB.*
*Kuwait added 2026-08-10: moh_kw_practice (40Q/60min) + moh_kw_full (100Q/180min) exam modes.*

### Spanish NCLEX Layer (G2) ✅ (2026-07-20, updated 2026-07-22)
- DB: 4 ES columns on mcq_questions (explanation_es, rationales_es, key_takeaway_es, test_taking_tip_es)
- Translation cron: `*/30 * * * * docker exec medmind_backend python -m app.scripts.translate_nclex_rationales --max 25`
  - Fixed (2026-07-22): now includes ordered/calculation questions (key_takeaway IS NOT NULL) — 112 new eligible
  - Total eligible: ~611 questions (499 MCQ/SATA + 112 ordered/calc)
- API: POST /exam/sessions/{id}/answers/{idx} returns ES fields alongside EN
- UI: RationalePanel language toggle 🇺🇸↔🇪🇸, localStorage persistence
- Public landing: `/es/nclex` — SEO Spanish NCLEX prep page
- Tests: 28 passed

### Regional Pricing (G3) ✅ (2026-07-20)
| Tier | Countries | Discount | Student | Pro | Gulf Bundle |
|------|-----------|----------|---------|-----|-------------|
| A | US/EU/GCC | — | $15 | $40 | $29 |
| B | TR/LatAm/CIS | 50% | $7.5 | $20 | $14.5 |
| C | IN/PH/EG/NG/PK | 70% | $4.5 | $12 | $8.7 |
- Region detection: CF-IPCountry → ip-api.com fallback; billing_country from Stripe = authoritative
- Anti-abuse: billing_country locked after first payment; unknown country defaults to Tier A
- Stripe: dynamic price_data used for Tier B/C; billing metadata stored in webhook
- PayPal: feature flag ready (PAYPAL_ENABLED=false), activate per-market when needed
- API: GET /pricing/regional — tier, country, source, prices, discount_pct
- UI: pricing page shows regional banner + crossed-out base price; exam landings show RegionalPriceBadge
- Tests: 43 passed

### V6 Phase 3 — NCLEX Readiness Score ✅ (2026-07-19)
- **`app/services/readiness.py`**: `compute_from_sessions()` + `compute_readiness()` + `get_cached_readiness()` + `invalidate_readiness_cache()`
  - Weights: NCLEX category distribution × recency (7d×1.5 / 30d×1.0 / older×0.5) × difficulty (easy×0.8 / hard×1.2)
  - Min threshold: 50 questions before score shown ("N more questions to go")
  - Levels: Below Passing / Borderline / Passing Range / High (thresholds: 55/62/75)
  - Weak categories: only pct < 75% with ≥5 questions, top-3
  - Redis cache: 1-hour TTL, invalidated on NCLEX session completion
- **API**: `GET /exam/nclex/readiness` — cached readiness + trend + category breakdown + disclaimer
- **Snapshot + per_question**: added `difficulty` field to both (needed for readiness weighting)
- **`finalize_session`**: invalidates readiness cache on NCLEX session submit
- **UI** (`nurses/nclex/page.tsx`):
  - New "Readiness" tab (2nd position after Practice)
  - Pre-threshold: progress bar "X/50 questions" with count
  - Post-threshold: 7xl score, level label, sparkline in score card, full 30-day bar chart with hover tooltips
  - Weak categories: bars + "Train this category →" button → jumps to Practice tab with category pre-selected
  - All category breakdown sorted ascending by pct, category labels clickable to train
  - Stats strip: readiness score shown if threshold met, clickable → opens Readiness tab
  - Disclaimer text on all states (legal: estimate, not NCLEX outcome prediction)
- **i18n**: `tab_readiness` + `readiness_label` added to all 7 locales (en/ru/es/fr/tr/ar/de)
- **Tests** `tests/test_v6_phase3.py`: 9 unit tests — threshold, weak category detection, recency weight, difficulty weight, trend sort, disclaimer

### V6 Phase 2 — NCLEX Rationales ✅ (2026-07-19)
- **DB migration** `k7l8m9n0o1p2`: added `rationales JSONB`, `key_takeaway TEXT`, `test_taking_tip TEXT`, `is_flagged BOOL`, `flag_reason TEXT` to `mcq_questions`
- **Generation**: MCQ + SATA prompts updated to return structured per-option rationales `{A: {text, why}}` + `key_takeaway` + `test_taking_tip`
- **Import script** updated to persist new fields
- **Backfill script**: `app/scripts/backfill_rationales.py --max N` (idempotent, batched, Groq content keys)
- **API**:
  - `POST /exam/sessions/{id}/answer` now returns `rationales`, `key_takeaway`, `test_taking_tip` for the answered question
  - `_build_results` includes rationales in `wrong_questions`
  - `POST /exam/questions/{id}/flag` — user flag endpoint (reason text)
  - `GET /exam/admin/flagged-questions` — admin list (admin role required)
  - `POST /exam/admin/flagged-questions/{id}/resolve` — clear flag
- **UI (exam/page.tsx)**:
  - `RationalePanel`: selected-option rationale always visible; other options collapsible; key_takeaway in amber callout; test_taking_tip in collapsed section
  - Practice mode (`nclex_demo`): rationale shown immediately after confirming answer
  - Timed exam modes: rationale only in results review
  - `FlagButton`: opens modal with optional reason text → POST flag endpoint
  - `ResultsView`: wrong questions show full `RationalePanel` in expanded view
- **Admin panel** (`admin/page.tsx`): new "🏴 NCLEX Flags" tab → `NclexFlaggedQuestionsPanel`

### V6 Phase 1 — Страховочная сетка ✅ (2026-07-19)
- **Playwright E2E** (11 passed, 1 skipped): `frontend/e2e/`, system Chromium, PLAYWRIGHT_BASE_URL
  - 10 smoke scenarios: register, lesson-complete, nclex-demo, dose-calc, flashcards(skip), ai-tutor-disclaimer, promo-checkout, public-contour(×3), search, language-switch
  - `global-setup.ts` seeds e2e_test@example.com user via `scripts/e2e_seed.py`
  - Root cause fixes found during E2E:
    - **register page bug** (`const res.data` double-unwrap) — register was broken for ALL users; fixed to `const data = await authApi.register(...)`
    - **double-render** in AppLayout (children rendered in both mobile + desktop containers) — fixed all E2E selectors by scoping to `main`
    - **helpers.ts API URL** — derived from PLAYWRIGHT_BASE_URL when NEXT_PUBLIC_API_URL not set
  - `npm run e2e` script added to package.json
- **Sentry frontend monitoring** — already configured in sentry.client/server/edge.config.ts ✅
- **Uptime monitor** — `scripts/ops/uptime_check.py`, Telegram alerts on state transitions
- **CI integration** — `.github/workflows/ci.yml` e2e job gates deploy on green tests
- **docs/MEDMIND_ROADMAP_V6.md** — full 6-phase roadmap created

### Tech Debt Resolved ✅ (2026-07-12)
- **TypeScript**: Fixed all 17 TS errors — was blocking clean `next build`
  - `locales/ar|de|es|fr|tr`: added `veterinary`, `no_vet_modules`, `stats_drugs`, `mode_vet`, `mode_vet_desc` to 5 locales
  - `admin/page.tsx`: removed nonexistent `token` field from AuthStore destructure
  - `articles/category/[cat]/page.tsx`: cast `speciesCounts` to `Record<string,number>`
- **Mobile Voice (V5 Phase 7.3)**: Complete
  - Added `expo-speech` (~13.0.0) + `expo-speech-recognition` (~0.2.0) to `mobile/package.json`
  - `mobile/app/(tabs)/ai.tsx` rewritten with voice mode:
    - Voice mode toggle → auto-TTS for AI responses via `Speech.speak()`
    - Mic button → `ExpoSpeechRecognitionModule.start()` STT
    - `pendingVoice` confirmation banner before sending (medical safety: Edit / Send / Cancel)
    - Graceful STT degradation if not available on device
    - **Requires `cd mobile && npm install` on device build**
- Commit: `69906e1`

### V5 Phase 7 — Voice Mode ✅ (2026-07-12)
- **VoiceMicButton**: forwardRef + `VoiceMicHandle.startListening()` for programmatic mic restart
- **VoiceMicButton**: `interimResults=true` — interim text shown in tooltip while recognizing
- **VoiceMicButton**: `patientMode` prop — blocks STT with explanatory tooltip (medical safety)
- **VoiceMicButton**: `autoStart` prop — re-starts on mount for conversation loop
- **VoiceMicButton**: visible "not supported" fallback (shows grayed icon instead of null)
- **VoiceSpeakButton**: `onEnded` callback for post-TTS actions (mic restart)
- **ConversationModeToggle**: new component; "Loop ON/OFF" button in header
- **ai-tutor page**: `pendingVoice` state — transcript shown for CONFIRMATION before sending
  (safety: avoids auto-sending mishears like "prednisone" vs "prednisolone")
- **Confirmation banner**: Heard → Edit / Send / Cancel UX
- **Auto-TTS**: after AI response streams, `ttsApi.speakBlob` plays audio when voiceMode active
- **Conversation loop**: `audio.onended` → `micRef.current.startListening()` when conversationMode active
- **voiceModeRef / conversationModeRef**: synced refs to avoid stale closure in async send()
- Commit: `ca417f0`

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
