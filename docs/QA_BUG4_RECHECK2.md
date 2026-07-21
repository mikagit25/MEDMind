# QA Re-Check 2 — Bug 4: Rationale Panel (Explanation Fallback Fix)

**Date:** 2026-07-21
**Commit:** `796eebf`
**Environment:** `https://medmind.pro`
**Previous QA doc:** `QA_TRANCHE1_RECHECK.md`

> **Scope:** Bug 4 was marked ❌ STILL BROKEN in the previous re-check.
> Root cause: 87% of questions have only `explanation` in the DB — not per-option
> `rationales`. The answer endpoint didn't return `explanation`, so the panel
> never rendered. This fix adds `explanation` to the response and shows it as
> a fallback in the panel.
>
> All other bugs (1, 2/3, 5, 8) were confirmed ✅ PASS in the previous re-check.
> Only spot-check regressions here.

---

## Fix 4.A — Panel appears for questions WITHOUT per-option rationales (~87%)

> This is the new behaviour. Most questions only have an `explanation` field.

1. Log in as pro-tier → `/exam` → **«NCLEX by Category»** → pick any category → Start
2. Answer any question and click **«Confirm Answer»**
3. ✅ «Answer Recorded» line appears immediately
4. ✅ A rationale panel appears **below** the «Answer Recorded / AI Explain / Flag» row
5. ✅ The panel contains a paragraph of explanatory text (the `explanation` field)
6. ❌ Bug would be: panel area is empty — only «Answer Recorded + AI Explain + Flag» visible

Answer 10 questions total (navigate with Next). Count how many show the panel.

| Expected | ≥ 8 out of 10 questions show a panel (explanation OR per-option rationale) |
|----------|---------------------------------------------------------------------------|

---

## Fix 4.B — Panel content variants

Two panel layouts are possible. Both are correct.

### Layout A — explanation fallback (expected for ~87% of questions)

```
┌──────────────────────────────────────────────────┐
│  [paragraph of explanation text]                 │
└──────────────────────────────────────────────────┘
```

- ✅ Plain text block, no «Option A: Correct/Incorrect» header
- ✅ No «Explain other options» collapsible (nothing to expand)
- ✅ EN/ES toggle NOT shown (no `rationales_es` for these questions)

### Layout B — per-option rationale (expected for ~13% of questions)

```
┌──────────────────────────────────────────────────┐
│  ✓ Option B: Correct                             │
│  [text explaining why B is correct]              │
├──────────────────────────────────────────────────│
│  💡 Key Takeaway                                 │
│  [key takeaway text]                             │
├──────────────────────────────────────────────────│
│  Explain other options (3)              [expand] │
└──────────────────────────────────────────────────┘
```

- ✅ Selected-option header with ✓ (green) or ✗ (red)
- ✅ «Key Takeaway» amber block
- ✅ «Explain other options» collapsible with remaining options
- ✅ EN/ES toggle visible if question has Spanish translation

---

## Fix 4.C — Rationale panel appears in Gulf practice mode

1. Log in as pro or gulf_bundle → `/exam` → **«SNLE Practice»** → Start
2. Answer any question → «Confirm Answer»
3. ✅ Panel appears (explanation or per-option rationale, either Layout A or B)
4. ❌ Bug would be: no panel in Gulf mode

---

## Fix 4.D — Panel appears in NCLEX Demo (unauthenticated)

1. Go to `/nurses/nclex` (no login needed) → Start demo
2. Answer any question → «Confirm Answer»
3. ✅ Panel appears
4. ❌ Bug: no panel in demo mode

---

## Fix 4.E — Timed full-sim still has NO panel (regression guard)

1. Log in as pro-tier → `/exam` → **«NCLEX-RN (75 questions)»** → Start
2. Answer any question → «Confirm Answer»
3. ✅ NO panel — only «Answer Recorded + AI Explain + Flag» visible
4. ❌ Bug would be: panel appears during timed exam (breaks the full-sim format)

Repeat for **«NCLEX-RN (85 questions)»** if available.

---

## Fix 4.F — Results screen still shows rationale/explanation (regression guard)

1. Complete any short NCLEX session (Quick 20 or Category practice) with at least one wrong answer
2. On the results screen, click on a wrong question to expand it
3. ✅ If question has per-option rationales → RationalePanel shows (Layout B)
4. ✅ If question has only explanation → explanation text block renders
5. ✅ Both: AI Explain + Flag buttons present

---

## Fix 4.G — EN/ES toggle works for the ~13% with Spanish translation

> Requires finding a question that has `rationales_es` populated.
> These are typically NCLEX questions tagged with a Spanish translation.

1. In-session: answer questions until you see **Layout B** panel with the EN/ES toggle visible
2. ✅ Toggle button «🇺🇸 English ↔ 🇪🇸 Español» visible at top-right of panel
3. Click toggle → ✅ text switches to Spanish («Correcta»/«Incorrecta», «Punto Clave»)
4. ✅ Language preference persists across navigation (Next/Prev) within the session
5. ✅ For Layout A questions (explanation only): toggle NOT shown

---

## Regression spot-checks (previously confirmed ✅, verify no breakage)

| Check | Steps | Expected |
|-------|-------|----------|
| Gulf modes in list | `GET /api/v1/exam/modes` (authenticated) | 7 Gulf modes present, each has `gulf: true` |
| `/exams/snle` loads | Open in browser | 200, h1 contains "SNLE", question count 200, pass score 500/800 |
| `/exams/gulf` table | Open in browser | 7-row comparison table, no "Exam data loading…" |
| Category filter | Start session with `nclex_category: "psychosocial"` | All questions tagged psychosocial/psychological variants |
| `/ar/gulf` html lang | `curl -sk https://medmind.pro/ar/gulf \| grep '<html'` | `lang="ar" dir="rtl"` |

---

## Priority order

`4.A (panel appears)` → `4.B (layout variants)` → `4.C (Gulf)` → `4.E (timed sim regression)` → `4.F (results screen)` → `4.D (demo)` → `4.G (EN/ES toggle)` → spot-checks

Report each item as ✅ Pass / ❌ Bug (with screenshot + steps to reproduce).
