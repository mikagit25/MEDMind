# MedMind AI — Error Log & Lessons Learned

> Log every error, wrong approach, and dead end HERE.
> Before trying something new, check this file to avoid repeating failures.

---

## Format
```
## [DATE] ERROR-ID: Short description
**Context:** What were you trying to do?
**Error/Symptom:** Exact error message or unexpected behavior
**Root Cause:** What actually went wrong
**Solution / Workaround:** What fixed it
**Avoid:** What NOT to do next time
```

---

## Resolved Issues

### [2026-04-03] ERR-001: passlib incompatible with bcrypt ≥ 4.0
**Context:** Installing bcrypt for password hashing  
**Error:** `AttributeError: module 'bcrypt' has no attribute '__about__'`  
**Root Cause:** passlib 1.7.4 uses `bcrypt.__about__.__version__` which was removed in bcrypt 4.0  
**Solution:** Use `bcrypt` directly without passlib. Added `bcrypt==4.1.3` to requirements, replaced `passlib.context.CryptContext` with direct `bcrypt.hashpw/checkpw` calls in `security.py`  
**Avoid:** Don't use passlib with bcrypt ≥ 4.0. Use bcrypt directly.

---

### [2026-04-03] ERR-002: pgvector extension not available on PostgreSQL 9.6
**Context:** Tried to CREATE EXTENSION vector on PG 9.6 Docker container  
**Error:** `ERROR: extension "vector" is not available`  
**Root Cause:** pgvector requires PostgreSQL 11+; the Docker container was using PG 9.6  
**Solution:** Gated pgvector behind `PGVECTOR_ENABLED=1` env var. Models use `JSONB` fallback for embeddings. `main.py` catches the extension error gracefully.  
**Avoid:** Don't assume pgvector is available. Always use the env var gate.

---

### [2026-04-03] ERR-003: UUID seed fix for specialties
**Context:** Seeding specialties in `main.py` lifespan  
**Error:** DB constraint violation on UUID column  
**Root Cause:** UUID was not being generated explicitly for the INSERT  
**Solution:** Used `str(_uuid.uuid4())` in the seed INSERT  
**Avoid:** Always generate UUID explicitly when inserting with UUID primary keys.

---

### [2026-04-03] ERR-004: next/font/google blocking frontend compilation
**Context:** Next.js 14 frontend startup  
**Error:** `Module not found: Can't resolve 'next/font/google'`  
**Root Cause:** The project used a custom font setup; `next/font/google` was imported but the font subsystem wasn't configured  
**Solution:** Removed the `next/font/google` import, switched to Tailwind `fontFamily` config  
**Avoid:** Don't use `next/font/google` unless the font is explicitly needed and configured.

---

### [2026-04-04] ERR-005: anthropic 0.88.0 partial install (broken dist-info)
**Context:** Upgrading anthropic package  
**Error:** `~nthropic` broken dist-info directory in venv; `import anthropic` failed  
**Root Cause:** Partial install left a corrupted dist-info  
**Solution:** Deleted `~nthropic-*.dist-info` from venv, reinstalled `anthropic==0.27.0`  
**Avoid:** If anthropic import fails, check for tilde-prefixed dist-info in `venv/lib/python*/site-packages/`.

---

### [2026-04-04] ERR-006: apscheduler missing from venv
**Context:** Backend startup  
**Error:** `ModuleNotFoundError: No module named 'apscheduler'`  
**Root Cause:** apscheduler not in requirements.txt initially  
**Solution:** Added `apscheduler>=3.10.4` to requirements.txt and installed in venv  
**Avoid:** Always add scheduler dependencies to requirements.txt during development.

---

### [2026-04-04] ERR-007: react-hot-toast missing dist/index.d.ts
**Context:** Frontend TypeScript compilation  
**Error:** `Cannot find module 'react-hot-toast' or its corresponding type declarations`  
**Root Cause:** Partial install of react-hot-toast (missing dist/ directory)  
**Solution:** Removed and reinstalled `react-hot-toast`  
**Avoid:** If a TS import fails for a known package, check that `dist/index.d.ts` exists.

---

### [2026-04-06] ERR-008: ClinicalCase.explanation AttributeError
**Context:** `POST /progress/cases/{id}/complete` in `routes/progress.py`  
**Error:** `AttributeError: 'ClinicalCase' object has no attribute 'explanation'`  
**Root Cause:** The SQLAlchemy `ClinicalCase` model has no `explanation` field — it has `teaching_points` (Array), `management` (Array), and `diagnosis` (String)  
**Solution:** Build explanation from `teaching_points`:
```python
teaching = case.teaching_points or []
explanation = (
    ". ".join(teaching) if teaching
    else (case.diagnosis or "Review the case carefully.")
)
```
**Avoid:** Don't assume model fields — always check `models/models.py` before accessing attributes.

---

### [2026-04-06] ERR-009: SQLAlchemy InvalidRequestError in SSE stream
**Context:** SSE event_stream generator in `routes/ai.py` — saving messages after streaming  
**Error:** `sqlalchemy.exc.InvalidRequestError: A transaction is already begun on this Session`  
**Root Cause:** SQLAlchemy 2.0 autobegin — after any DB query, the session starts a transaction automatically. Calling `async with db.begin():` inside the generator (after a prior query) tries to start a second nested transaction, which is not allowed.  
**Solution:** Removed `async with db.begin():` context manager. Used plain `db.add()` + `await db.commit()`:
```python
db.add(user_msg)
db.add(ai_msg)
await db.commit()
```
**Avoid:** Never use `async with db.begin():` after any prior DB operation in the same session. With SQLAlchemy 2.0 autobegin, just call `db.add()` + `await db.commit()` directly.

---

### [2026-04-06] ERR-010: Flashcard page used front/back instead of question/answer
**Context:** `frontend/app/(app)/flashcards/page.tsx`  
**Error:** Flashcards rendered blank — `currentCard.front` and `currentCard.back` were `undefined`  
**Root Cause:** The `Card` TypeScript type defined `front`/`back` fields, but the API returns `question`/`answer`  
**Solution:** Updated Card type to `{ question: string; answer: string; ... }` and all usage sites  
**Avoid:** Always check the actual API response shape in `routes/content.py` before defining frontend types.

---

### [2026-04-06] ERR-011: Cases page multiple field name mismatches + wrong data source
**Context:** `frontend/app/(app)/cases/page.tsx`  
**Error:** (a) Used `getSpecialties()` as source for modules — specialties have `name` not `title`; (b) `c.chief_complaint` → field doesn't exist (use `c.presentation`); (c) `selected.scenario` → doesn't exist (use `selected.presentation`); (d) `selected.vitals` rendered as string but is a dict  
**Root Cause:** Initial implementation used wrong API + wrong field names  
**Solution:** Complete rewrite — two-level selector (specialty → module), `formatVitals()` helper, correct field names (`presentation`, `differential_diagnosis`)  
**Avoid:** Check API route response shape before building frontend. Cases come from `GET /modules/{id}/cases`, not from specialties.

---

### [2026-04-06] ERR-012: Lesson content JSONB rendered via dangerouslySetInnerHTML
**Context:** `frontend/app/(app)/modules/[id]/page.tsx`  
**Error:** Lesson content shown as `[object Object]` or blank  
**Root Cause:** `content` field is JSONB `{intro, sections, clinical_pearl, key_points}`, but the page used `dangerouslySetInnerHTML={{ __html: content }}`  
**Solution:** Created `LessonContentRenderer` component that handles both dict format and string format  
**Avoid:** Never use `dangerouslySetInnerHTML` on JSONB content from API. Always check content shape first.

---

### [2026-04-06] ERR-013: Progress page weaknesses wrong data shape
**Context:** `frontend/app/(app)/progress/page.tsx`  
**Error:** `weaknesses` always empty array even when backend returned data  
**Root Cause:** (a) `weakRes.data` was used directly but backend returns `{weaknesses: [...]}` not an array; (b) rendering used `w.topic` (doesn't exist) and `w.correct_rate` (doesn't exist)  
**Solution:** Used `weakRes.data?.weaknesses ?? []`; rendered based on `w.reason` field:
- `"low_flashcard_score"` → `w.module_title` + `w.avg_quality`
- `"low_completion"` → `w.module_title` + `w.completion_percent`  
**Avoid:** Always log/inspect API response shape before mapping to UI state.

---

### [2026-04-06] ERR-014: Alembic initial migration schema mismatch
**Context:** `alembic/versions/0001_initial_schema.py`  
**Error:** Migration used `Integer` PKs, `front`/`back` flashcard columns, missing tables (courses, course_modules, course_enrollments, course_assignments), wrong user_bookmarks structure, missing columns in many tables  
**Root Cause:** Initial migration was written before the models were finalized  
**Solution:** Complete rewrite of `0001_initial_schema.py` to match current SQLAlchemy models exactly — UUID PKs, correct column names, all 23 tables  
**Avoid:** Always regenerate/update Alembic migration when models change significantly.

---

### [2026-04-06] ERR-015: courses.py not mounted in main.py
**Context:** `courses.py` router existed but backend had no courses API endpoints
**Error:** `GET /api/v1/courses/...` → 404 Not Found  
**Root Cause:** `courses` not imported or included in `main.py`  
**Solution:** Added `from app.api.v1.routes import ... courses` and `app.include_router(courses.router, prefix=API_PREFIX)`  
**Avoid:** After creating a new router file, always add it to `main.py`.

---

### [2026-04-06] ERR-016: courses.py GET /enrolled route conflict
**Context:** `GET /courses/enrolled` returns enrolled courses for students  
**Error:** FastAPI would match `/enrolled` against `/{course_id}` (UUID) defined earlier, returning 422 instead of the student list  
**Root Cause:** Fixed-path routes must be defined BEFORE dynamic `/{param}` routes in FastAPI  
**Solution:** Moved `POST /join` and `GET /enrolled` before `GET /{course_id}` in the file  
**Avoid:** Always put literal path routes (`/join`, `/enrolled`, `/me`) before dynamic `/{id}` routes.

---

### [2026-04-06] ERR-017: search/page.tsx data shape mismatch
**Context:** `GET /search` returns `{modules: [...], lessons: [...], total: N}` but frontend did `setResults(res.data)` treating it as an array  
**Error:** `results.map(...)` called on an object → no items displayed  
**Root Cause:** Frontend assumed flat array; backend returns structured object  
**Solution:** Normalize in frontend:
```ts
const flat = [
  ...(data.modules ?? []).map(m => ({ id: m.id, type: "module", title: m.title })),
  ...(data.lessons ?? []).map(l => ({ id: l.id, type: "lesson", title: l.title, module_id: l.module_id })),
];
```
**Avoid:** Always inspect backend response shape before mapping to UI state.

---

### [2026-04-06] ERR-018: progress/stats hardcoded zeros
**Context:** `GET /progress/stats` returned `lessons_completed=0, mcqs_answered=0, correct_rate=0.0` always  
**Root Cause:** `get_stats` route had `lessons_completed=0, mcqs_answered=0` hardcoded instead of calculated  
**Solution:** Calculate from `UserProgress` aggregate: `sum(len(p.lessons_completed or []))`, `sum(p.mcq_attempts or 0)`, weighted avg for `correct_rate`. Added `modules_started` field.  
**Avoid:** Don't leave placeholder zeros in stats routes. Also — frontend used `stats?.modules_started` but schema only had `modules_in_progress`.

---

### [2026-04-06] ERR-019: progress/history display format mismatch
**Context:** `GET /progress/history` returns `[{date, lessons, cards, xp_gained}]` (day aggregates, 30 items)  
**Error:** Frontend rendered each item with `item.type` (undefined), `item.title` (undefined), showing 30 blank entries  
**Root Cause:** Frontend expected event list format `[{type, title, date, xp_gained}]` but backend returns day-aggregated format  
**Solution:** Fixed frontend to filter days with activity and display `"3 lessons · 10 cards reviewed"` summary per day  
**Avoid:** API history endpoint returns day-by-day aggregates, not per-event log.

---

## Dead Ends / Approaches That Did NOT Work

- `async with db.begin():` inside async generator after a prior DB read → InvalidRequestError (use plain add + commit)
- `passlib.context.CryptContext` with `bcrypt ≥ 4.0` → AttributeError (use bcrypt directly)
- `dangerouslySetInnerHTML` on JSONB lesson content → `[object Object]` (use renderer component)

---

## Performance Notes

- `GET /admin/modules` does N+1 queries (4 COUNT queries per module). For large datasets, consolidate with subqueries or cached counts. Currently acceptable for admin use.

---

## Security Notes

- JWT secret is hardcoded in PROJECT_STATE.md — must be replaced with a real 256-bit random secret before production
- `ANTHROPIC_API_KEY=sk-ant-your-key-here` — placeholder, must be replaced before testing AI features

---

## Dependency Conflicts

| Package | Version | Conflict | Resolution |
|---------|---------|----------|------------|
| passlib | 1.7.4 | Incompatible with bcrypt ≥ 4.0 | Use bcrypt directly |
| pgvector | 0.2.5 | Requires PostgreSQL 11+ | Gate behind PGVECTOR_ENABLED=1 |
| anthropic | 0.27.0 | Partial install can corrupt dist-info | Reinstall if import fails |
