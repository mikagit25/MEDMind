# QA Re-Check — MedMind EXAMS-GLOBAL Tranche 1 · Bug Fix Verification

**Date:** 2026-07-21
**Commit:** `c6148ae`
**Environment:** `https://medmind.pro`
**API base:** `/api/v1`
**Accounts needed:** free-tier, student-tier, gulf_bundle-tier, pro-tier, admin

> This document covers only the bugs that were fixed in commit `c6148ae`.
> Test these in priority order. Each section ends with the exact DoD the previous
> QA defined — pass/fail against those criteria.

---

## Fix 1 — Gulf exam access control (Bug 1)

### 1.1 GET /api/v1/exam/modes — Gulf modes now present

```bash
# Authenticated as any user (e.g. pro-tier)
GET /api/v1/exam/modes
```

✅ Response is a JSON array that includes entries for all 7 Gulf modes:
`snle_practice`, `dha_practice`, `qchp_practice`, `omsb_practice`,
`nhra_practice`, `mohuae_practice`, `haad_practice`

For each Gulf mode verify the object contains:
- `"id"`: one of the 7 slugs above
- `"exam_slug"`: the exam slug (e.g. `"snle"`)
- `"pass_threshold"`: `65`
- `"gulf"`: `true`

### 1.2 Tier gating — free/student tier blocked

```
POST /api/v1/exam/sessions
Body: {"mode_id": "snle_practice"}
```

| Tier | Expected |
|------|----------|
| free | ❌ 403 — message contains "Gulf Bundle" or "Pro subscription" |
| student | ❌ 403 — same |
| gulf_bundle | ✅ 201 — session created |
| pro | ✅ 201 — session created |
| clinic | ✅ 201 — session created |

Repeat the 403 check for at least 2 other Gulf modes (e.g. `dha_practice`, `qchp_practice`).

### 1.3 Gulf session serves nursing questions

After creating a session as pro-tier (`POST /api/v1/exam/sessions {"mode_id": "snle_practice"}`):

```
GET /api/v1/exam/sessions/{id}
```

✅ `questions` array is non-empty (up to 50 questions for SNLE)
✅ Questions have `nclex_client_needs` field (blueprint categories)
✅ Session does NOT serve USMLE/non-nursing questions (all come from nursing modules)

---

## Fix 2 & 3 — Gulf landing pages no longer 404 / loading placeholder (Bugs 2 & 3)

### 2.1 Individual exam pages — HTTP 200

Load each URL directly in a browser (no internal navigation, use a fresh tab):

| URL | Expected |
|-----|----------|
| `/exams/snle` | ✅ 200 — exam name, country, params, categories |
| `/exams/dha` | ✅ 200 |
| `/exams/qchp` | ✅ 200 |
| `/exams/omsb` | ✅ 200 |
| `/exams/nhra` | ✅ 200 |
| `/exams/moh-uae` | ✅ 200 |
| `/exams/haad` | ✅ 200 |

On each page verify:
- ✅ Exam name rendered in `<h1>` (e.g. «SNLE — Saudi Nursing Licensing Exam»)
- ✅ Country, regulatory body, question count, duration, pass mark visible
- ✅ Blueprint categories section shows at least 8 cards (including **Critical Care Nursing** — newly added)
- ✅ Non-affiliation disclaimer text present
- ✅ Link to official source opens in new tab
- ✅ Gulf Bundle CTA section present
- ✅ `<title>` contains the exam name (view page source)
- ✅ `<link rel="alternate" hreflang="ar">` in `<head>` (DevTools → Elements)
- ✅ SNLE specifically: question count shows **200**, duration **4h30m**, pass score **500/800**

### 2.2 /exams/gulf — comparison table populated

Load `/exams/gulf` (hard refresh, Ctrl+Shift+R):

✅ Page never shows «Exam data loading…» placeholder — table appears on first load
✅ Comparison table has exactly **7 rows** (one per Gulf exam)
✅ Each row: country, authority, question count, duration, pass %
✅ «Explore Each Exam» section shows 7 clickable cards
✅ Each card links to `/exams/<slug>` (which now loads correctly per Fix 2.1)

---

## Fix 4 — EN/ES rationale toggle (Bug 4)

### 4.1 Rationale panel appears immediately for category practice

1. Log in as pro-tier → `/exam` → choose **«NCLEX by Category»** → pick any category → Start
2. Answer any question
3. ✅ Rationale panel appears **immediately after clicking «Confirm Answer»** (no need to submit)
4. ✅ Panel shows: selected option rationale (correct/incorrect), Key Takeaway, «Explain other options» toggle
5. ❌ Bug would be: panel hidden, only «Answer Recorded + AI Explain + Flag» buttons visible

### 4.2 Rationale appears immediately for Gulf practice mode

1. Log in as gulf_bundle or pro-tier → `/exam` → choose **«SNLE Practice»** → Start
2. Answer any question
3. ✅ Rationale panel appears immediately after confirming answer
4. ✅ Same structure: selected rationale + Key Takeaway

### 4.3 Rationale hidden during timed full-sim NCLEX

1. Log in as pro-tier → `/exam` → choose **«NCLEX-RN (75 questions)»** → Start
2. Answer any question
3. ✅ NO rationale panel — only «Answer Recorded + AI Explain + Flag» visible
4. Rationale appears only after full submission in the results screen (see 4.5)

### 4.4 EN/ES toggle in session rationale (for translated questions)

> Requires at least one question with `rationales_es` non-null.
> Verify via API first: answer a question and check `POST /api/v1/exam/sessions/{id}/answer`
> response — if `rationales_es` is non-null, the toggle must appear.

For a question with `rationales_es` populated:
1. ✅ Toggle **«🇺🇸 English ↔ 🇪🇸 Español»** visible at top-right of rationale panel
2. Click toggle → ✅ text switches to Spanish («Correcta»/«Incorrecta», «Punto Clave», «Explicar otras opciones»)
3. Refresh page (stay in same session) → ✅ Spanish preference preserved
4. Click again → ✅ switches back to English

For a question with `rationales_es = null`:
5. ✅ Toggle NOT shown — only English rationale visible

### 4.5 EN/ES toggle in results review screen

1. Complete any NCLEX session (including timed full-sim) with at least one wrong answer
2. On the results screen, expand a wrong question
3. If the question has `rationales_es` populated → ✅ toggle visible, works the same as 4.4
4. If `rationales_es = null` → ✅ toggle not shown
5. ✅ Language preference (localStorage) is shared between in-session and results view

---

## Fix 5 — Multilingual pages: `<html lang>`, `dir`, hreflang (Bug 5)

Test each URL below. For each: **view page source** (Ctrl+U or `curl`) — NOT DevTools
computed DOM — because we need to verify the SSR-rendered HTML, not the client-modified DOM.

| URL | Expected `<html lang>` | Expected `dir` | Extra check |
|-----|------------------------|----------------|-------------|
| `/ar/gulf` | `lang="ar"` | `dir="rtl"` | Arabic body text |
| `/ru/gulf` | `lang="ru"` | `dir="ltr"` | Russian body text |
| `/tr/gulf` | `lang="tr"` | `dir="ltr"` | Turkish body text |
| `/de/gulf` | `lang="de"` | `dir="ltr"` | German body text |
| `/fr/gulf` | `lang="fr"` | `dir="ltr"` | French body text |
| `/es/gulf` | `lang="es"` | `dir="ltr"` | Spanish body text |
| `/exams/gulf` | `lang="en"` | `dir="ltr"` | English (no regression) |
| `/` | `lang="en"` | `dir="ltr"` | English (no regression) |

For `/ar/gulf` specifically:
- ✅ `<html lang="ar" dir="rtl">` in raw HTML source
- ✅ Page layout is RTL — text aligned right, cards flow right-to-left
- ✅ 7 exam cards present in Arabic

**Regression — generic locale pages still work:**
| URL | Expected |
|-----|----------|
| `/ru` | ✅ 200 — Russian landing page loads |
| `/ar` | ✅ 200 — Arabic landing page loads |
| `/tr` | ✅ 200 — Turkish landing page loads |

---

## Fix 8 — Category filter returns only the requested category (Bug 8)

### 8.1 Session questions match the selected category

1. Log in as pro-tier → `POST /api/v1/exam/sessions {"mode_id": "nclex_category", "nclex_category": "psychosocial"}`
2. Get session: `GET /api/v1/exam/sessions/{id}`
3. Inspect `questions` array — check the `nclex_client_needs` field on each question
4. ✅ Every question has `nclex_client_needs` in:
   `["psychosocial", "psychosocial_integrity", "psychological", "communication",
   "psychological_integrity", "communication_and_documentation"]`
5. ❌ Bug would be: questions tagged `safe_effective_care`, `physiological_adaptation`, etc. appear

Repeat for 2 more categories:

**Category: `pharmacological`**
- ✅ All questions in `["pharmacological", "pharmacological_therapies", "pharmacological_and_parenteral"]`

**Category: `safe_effective_care`**
- ✅ All questions in `["safe_effective_care", "safe_effective_care_environment", "safety",
  "safety_infection_control", "management_of_care", "safe_effective"]`

### 8.2 Category UI workflow

1. Log in as pro-tier → `/nurses/nclex` → Practice tab → NCLEX by Category → select «Psychosocial Integrity» → Start
2. ✅ Session starts successfully
3. All questions are tagged with the psychosocial category (verify via API or check nclex_client_needs badge in UI)

---

## Regression — Items NOT changed, must still pass

### R.1 NCLEX core flow

1. Start NCLEX Practice (nclex_demo mode, no auth needed) → answer 5 questions
2. ✅ «Confirm Answer» works
3. ✅ Rationale panel shows (demo mode IS practice mode)
4. ✅ AI Explain button opens
5. ✅ Flag question works
6. ✅ Prev/Next navigation works
7. Submit → ✅ Results screen shows score + category breakdown

### R.2 Middleware locale routing — no regression

| URL | Expected behaviour |
|-----|--------------------|
| `/ru/articles/some-slug` | ✅ Rewrites to `/articles/some-slug?lang=ru` — article loads in Russian |
| `/es/nclex` | ✅ Dedicated page loads (bypass path, NOT rewritten) |
| `/ar/nclex-snle` | ✅ Dedicated page loads (bypass path, NOT rewritten) |
| `/tr/gulf` | ✅ Dedicated page loads with `lang="tr"` in source |

### R.3 Exam definitions API — no regression

```
GET /api/v1/exam/definitions           → 200, list includes Gulf + any other active exams
GET /api/v1/exam/definitions/family/gulf → 200, exactly 7 records
GET /api/v1/exam/definitions/snle      → 200, question_count=200, passing_score_label="500/800"
GET /api/v1/exam/definitions/nonexistent → 404
```

### R.4 Root layout lang attribute — no regression on non-locale pages

View source (not DevTools) on:
- `/pricing` → `<html lang="en">`
- `/drugs` → `<html lang="en">`
- `/articles` → `<html lang="en">`
- `/` → `<html lang="en">`

---

## Out of scope for this re-check

These items were NOT fixed in this sprint:

| Item | Reason | Status |
|------|---------|--------|
| Bug 6 — Update button stays red | Code is correct; likely a hover-state misread in QA. Needs re-test with network tab open to confirm 200 response + visual state change | Needs re-test, not a code bug |
| Bug 7 — Self-referral not blocked | `QA_TESTER_2026` code belongs to a different user (not the admin), so "NOT BLOCKED" is the correct result. Needs re-test with an affiliate code that IS owned by the logged-in admin | Needs re-test with correct setup |
| Block 3 — Regional pricing | Requires real IPs or VPN to test CF-IPCountry; no code bug found | Out of scope |

---

## Priority order

`Fix 1 (Gulf modes)` → `Fix 2 & 3 (landing pages)` → `Fix 8 (category filter)` → `Fix 4 (ES toggle)` → `Fix 5 (lang/dir)` → `R.1–R.4 (regression)`

Report each item as ✅ Pass / ❌ Bug (with screenshot + steps to reproduce).
