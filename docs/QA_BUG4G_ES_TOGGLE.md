# QA Task — Bug 4.G: EN/ES Rationale Toggle

**Date:** 2026-07-21
**Commit:** `0b6dedc`
**Prerequisite:** Bug 4.A–4.F confirmed ✅ PASS (commit `796eebf`)

---

## Root Cause (resolved)

All `rationales_es` / `explanation_es` columns were NULL for every question.
Three issues fixed:
1. The translation pipeline was silently failing because Groq's retry-after message
   (`"44m47.04s"`) wasn't parsed correctly — the script defaulted to 60s and then
   exhausted its retry budget before rate limits reset.
2. The pipeline was also translating veterinary questions instead of NCLEX questions.
3. The scheduler was requesting 50 questions per run — too many for the per-minute
   token quota.

**Current state:** 2 NCLEX questions have Spanish data. Scheduler runs every 30 min
at :15 and :45 UTC (10 questions per run) and will populate the remaining ~155 over
the next few hours.

---

## Known Spanish-translated questions (for immediate UI testing)

| ID | Category | Question preview |
|----|----------|-----------------|
| `a613f327-8bcd-4f2f-b305-208761457e58` | `physiological_adaptation` | "A nurse is assessing a patient's pain level using the ADPIE framework…" |
| `a2bc93e9-bad2-4c9d-a5eb-709dc1bcebfe` | `safe_effective_care` | "A nurse is caring for a patient with a central line and notices that the dressing…" |

Both questions have `rationales_es`, `key_takeaway_es`, and `explanation_es` populated.

---

## How to reach these questions in the UI

### Option A — Target by category (easiest)

1. Log in as pro-tier → `/exam`
2. Choose **«NCLEX by Category»** → **«Physiological Adaptation»** → Start
3. Answer questions one by one until you see the question containing **"ADPIE framework"**
4. Answer it and confirm → ✅ the EN/ES toggle button should appear

Or:
1. Choose **«NCLEX by Category»** → **«Safe/Effective Care»** → Start
2. Look for the question about **"central line dressing"**

### Option B — Direct API verification (faster for confirming data is present)

```bash
# Create a session (requires auth token)
POST /api/v1/exam/sessions
{"mode_id": "nclex_category", "nclex_category": "physiological_adaptation"}

# Answer question at index 0 with any option
POST /api/v1/exam/sessions/{id}/answer
{"question_index": 0, "selected_option": "A"}

# Check response — look for non-null rationales_es
```

If the first question in the session is not `a613f327`, keep answering until you find it.
You can also verify the data directly:

```bash
GET /api/v1/exam/sessions/{id}   # inspect questions array for question IDs
```

---

## Test Checklist

### 4.G.1 — EN/ES toggle visible when rationales_es is present

1. Start a `physiological_adaptation` category session (pro-tier)
2. Find and answer the ADPIE question (question ID `a613f327…`)
3. After clicking «Confirm Answer»:
4. ✅ Rationale panel appears (this was fixed in 4.A — should be passing)
5. ✅ **EN/ES toggle button** appears at top-right of the panel:
   - Label: «🇺🇸 English» with «↔» arrow when in English mode
   - OR «🇪🇸 Español» when in Spanish mode

### 4.G.2 — Toggle switches panel text to Spanish

1. (Continuing from 4.G.1) — panel is showing English text
2. Click the toggle button
3. ✅ Selected-option header switches to: «Opción B: Correcta» (or «Incorrecta»)
4. ✅ Key Takeaway label switches to: «Punto Clave»
5. ✅ «Explain other options» button switches to: «Explicar otras opciones (N)»
6. ✅ Option texts are now in Spanish (medical professional Spanish)

### 4.G.3 — Spanish preference persists across navigation

1. (Toggle is ON — showing Spanish)
2. Click **«Next»** to go to the next question and answer it
3. Come back to the ADPIE question via **«Prev»**
4. ✅ Panel still shows Spanish (not reset to English)

### 4.G.4 — Toggle switches back to English

1. (Panel showing Spanish)
2. Click toggle again
3. ✅ All text switches back to English

### 4.G.5 — Toggle hidden for questions without Spanish data

1. In the same session, find any question that does NOT show the toggle
2. ✅ No toggle button visible — only English rationale (or explanation)
3. ❌ Bug would be: toggle shows but clicking it shows no text / blank panel

### 4.G.6 — Results screen toggle (after session complete)

1. Complete the category session
2. On the results screen, expand a wrong question (if any)
3. If the expanded question is `a613f327` or `a2bc93e9`:
   - ✅ Same EN/ES toggle visible in results panel
   - ✅ Clicking toggle works the same as in-session
4. ✅ Language preference from in-session carries over to results (localStorage key
   `nclex_rationale_lang`)

---

## Translation Pipeline Status (ongoing)

The scheduler at `:15` and `:45` UTC will continue translating NCLEX questions.
After the next few cron runs, there should be 10–30 questions with Spanish data.

To check current count at any time:
```sql
SELECT COUNT(*) FROM mcq_questions WHERE rationales_es IS NOT NULL AND nclex_client_needs IS NOT NULL;
```

Expected growth: +10 questions every ~30 minutes until all 157 are translated.

---

## Regression Smoke Test (4.A–4.F)

After testing 4.G, verify no regression:

| Check | Expected |
|-------|----------|
| Start any practice session, answer a question | Panel appears (Layout A or B) |
| Start NCLEX-RN 75 (timed), answer a question | NO panel during timed exam |
| Complete a session, expand wrong question in results | Panel/explanation renders + AI Explain + Flag |

Report each item as ✅ Pass / ❌ Bug (screenshot + repro steps).
