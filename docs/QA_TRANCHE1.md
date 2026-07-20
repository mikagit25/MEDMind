# QA Task — MedMind EXAMS-GLOBAL Tranche 1 (G1 + G2 + G3)

**Date:** 2026-07-20
**Environment:** `https://medmind.pro` (prod) or `http://localhost:3000` (dev)
**API base:** `/api/v1`
**Accounts needed:** admin, student-tier, pro-tier, free-tier

---

## Block 0 — QA Bug Fixes (regression from previous sprint)

### 0.1 Update button in Reschedule Exam Date
1. Log in as any authenticated user → `/nurses/nclex`
2. Set an exam date → click **Update**
3. ✅ Expected: button turns **green** «Saved ✓» for 2 seconds, then returns to normal state
4. ❌ Bug: if button turns red or stays grey on a successful 200 response — report it

### 0.2 «↺ Refresh» button in promo code list (Admin)
1. Log in as admin → `/admin` → **Promo** tab
2. In another tab, apply a promo code as a test user
3. Return to admin panel → click **↺ Refresh** (no page reload)
4. ✅ Expected: list updates, new use count is visible

### 0.3 QA tools in Lifecycle panel (Admin)
1. Admin → `/admin` → **Lifecycle** tab
2. ✅ Must have: «QA Tools» section with:
   - Affiliate code input + **Simulate Referral Signup** button
   - Campaign dropdown + **Send Test Email** button
3. Click **Simulate Referral** with a valid code → expect JSON with `self_referral_check` and `cross_user_check`
4. Click **Send Test Email** → expect email delivered to the admin's email address

---

## Block 1 — G1: Gulf Prometric Exam Registry

### 1.1 API — Exam registry

```
GET /api/v1/exam/definitions
GET /api/v1/exam/definitions/family/gulf
GET /api/v1/exam/definitions/snle
GET /api/v1/exam/definitions/dha
```

For each, verify:
- ✅ HTTP 200
- ✅ Fields present: `slug`, `name`, `country`, `regulatory_body`, `question_count`, `duration_min`, `pass_threshold`, `blueprint_source`, `status`
- ✅ `status = "draft"` for all 7 exams (Gulf not activated until blueprint verified)
- ✅ Family endpoint returns exactly 7 records

Non-existent slug:
```
GET /api/v1/exam/definitions/nonexistent
```
- ✅ HTTP 404

### 1.2 Public landing pages

| URL | Check |
|-----|-------|
| `/exams` | Hub with links to NCLEX, Gulf, UK families |
| `/exams/gulf` | Comparison table of 7 exams (country / authority / Q count / duration / pass%) |
| `/exams/snle` | Landing: name, country, exam params, blueprint categories |
| `/exams/dha` | Same |
| `/exams/qchp` | Same |
| `/exams/omsb` | Same |
| `/exams/nhra` | Same |
| `/exams/moh-uae` | Same |
| `/exams/haad` | Same |

On every exam landing, verify:
- ✅ Non-affiliation disclaimer text: «MedMind AI is not affiliated with...»
- ✅ Link to official source (regulatory body) opens in a new tab
- ✅ Gulf Bundle CTA section is present
- ✅ `<title>` meta tag contains the exam name

### 1.3 Exam access control

| Account type | Expected access to Gulf exam |
|---|---|
| free | ❌ no access (demo only) |
| student | ❌ no access to Gulf (NCLEX only) |
| gulf_bundle | ✅ all 7 Gulf exams |
| pro | ✅ all exams |
| clinic | ✅ all exams |

Verify via API:
```
POST /api/v1/exam/sessions   body: {"mode_id": "snle_practice"}
```
- Under student tier → expect 403 or upgrade prompt
- Under pro tier → expect 200

---

## Block 2 — G2: Spanish NCLEX Layer

### 2.1 DB — ES columns present

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'mcq_questions'
AND column_name LIKE '%_es';
```
✅ Must return: `explanation_es`, `rationales_es`, `key_takeaway_es`, `test_taking_tip_es`

### 2.2 API — ES fields in answer response
1. Start an NCLEX Practice session → answer any question
2. `POST /api/v1/exam/sessions/{id}/answers/{idx}`
3. ✅ Response contains keys: `rationales`, `key_takeaway`, `rationales_es`, `key_takeaway_es`, `test_taking_tip_es`, `explanation_es`
4. `rationales_es = null` is acceptable (translation not yet run); if `rationales` is present but `_es` keys are absent entirely — that's a bug

### 2.3 UI — Language toggle in RationalePanel

For questions that have `rationales_es` populated (need at least one translated question):

1. Do an NCLEX Practice session → answer a question
2. If the question has an ES translation → ✅ toggle «🇺🇸 English ↔ 🇪🇸 Español» is visible at the top of the explanation block
3. Click toggle → ✅ explanation text switches to Spanish («Correcta»/«Incorrecta», «Punto Clave», «Explicar otras opciones»)
4. Refresh the page → ✅ language preference is preserved (localStorage)
5. Click again → ✅ switches back to English
6. For questions WITHOUT a translation → ✅ toggle is not visible, only EN shown

### 2.4 Public landing `/es/nclex`
- ✅ Page loads without authentication
- ✅ `<h1>` contains «NCLEX» and «español»
- ✅ Non-affiliation disclaimer present (re: NCSBN/NCLEX)
- ✅ CTA links to `/register`
- ✅ «Ver en inglés» link goes to `/nurses/nclex`
- ✅ 4 feature blocks: «Explanaciones en español», «3 000 preguntas», «Tutor de IA», «Modo adaptativo»
- ✅ FAQ section with 4 questions

### 2.5 Translation script — smoke test (dry-run)
```bash
docker exec medmind_backend python3 -m app.scripts.translate_nclex_rationales --dry-run
```
✅ Output: `Found N questions to translate` + `[DRY RUN] No writes will be made.`
✅ No Python exception

---

## Block 3 — G3: Regional Pricing

### 3.1 API endpoint — region detection
```
GET /api/v1/pricing/regional       # unauthenticated
GET /api/v1/pricing/all-tiers      # full table
```
✅ HTTP 200
✅ `regional` response contains: `tier`, `country`, `source`, `prices`, `base_prices`, `discount_pct`, `currency`
✅ `currency = "USD"`
✅ `prices["student"]` ≤ `base_prices["student"]`
✅ `discount_pct` is 0, 50, or 70

### 3.2 Regional price test matrix

Simulate requests with different countries via header (curl/Postman):
```bash
# Tier C — Philippines
curl -H "CF-IPCountry: PH" /api/v1/pricing/regional

# Tier B — Turkey
curl -H "CF-IPCountry: TR" /api/v1/pricing/regional

# Tier A — USA (default)
curl /api/v1/pricing/regional
```

| Country | Expected tier | Expected student price | Expected discount_pct |
|---------|--------------|------------------------|----------------------|
| PH | C | $4.5 | 70 |
| EG | C | $4.5 | 70 |
| IN | C | $4.5 | 70 |
| TR | B | $7.5 | 50 |
| MX | B | $7.5 | 50 |
| US | A | $15.0 | 0 |
| SA | A | $15.0 | 0 |
| ZZ (unknown) | A | $15.0 | 0 |

### 3.3 `/pricing` page — regional banner

1. Open `/pricing` with header `CF-IPCountry: PH` (or from a PH IP)
2. ✅ Green banner visible: «🌍 70% regional discount applied»
3. ✅ Student plan card shows `$4` (regional) with strikethrough `$15` (base)
4. Open from a US/EU IP without the header:
5. ✅ No banner shown, standard prices

### 3.4 `/exams/snle` — RegionalPriceBadge

1. Open `/exams/snle` from PH IP / with PH header
2. ✅ In Gulf Bundle CTA section: badge «🌍 Regional price: $8/mo (70% off)» is visible
3. From US IP:
4. ✅ Badge not shown

### 3.5 Anti-abuse — unknown country

```bash
curl -H "CF-IPCountry: XX" /api/v1/pricing/regional
```
✅ `tier = "A"`, `discount_pct = 0`
✅ Unknown code never grants a discount

### 3.6 Anti-abuse — billing_country lock after payment

*(Requires test Stripe with real webhook)*
1. Complete a payment with PH billing address
2. Check DB: `SELECT billing_country, billing_region FROM users WHERE id = '...'`
3. ✅ `billing_country = "PH"`, `billing_region = "C"`
4. Call `/pricing/regional` again from US IP → ✅ `source = "billing"`, `tier = "C"` (billing_country takes priority)

---

## Block 4 — Sitemap

```bash
curl https://medmind.pro/sitemap-en.xml | grep -E "es/nclex|exams/"
```

✅ URLs present:
- `/es/nclex`
- `/exams`
- `/exams/gulf`
- `/exams/snle` (and the other 6 Gulf exam slugs)

---

## Block 5 — NCLEX Core Flow Regression

After all changes, verify nothing is broken:

1. Start NCLEX Practice session → answer 3 questions → ✅ progress saved
2. «Confirm Answer» button → ✅ works
3. Rationale panel (EN) → ✅ displays without errors
4. AI Explain button → ✅ opens chat
5. Flag question → ✅ marks the question
6. Prev/Next navigation → ✅ no state reset
7. Submit exam → Results screen → ✅ shows score and category breakdown

---

## Report Format

For each item, record:
- ✅ Pass / ❌ Bug (with description and screenshot)
- Browser, OS
- Specific URL and reproduction steps for any bug

**Priority order:** 3.2 (price matrix) → 2.3 (ES toggle) → 1.2 (Gulf landings) → 0.x (fix regression) → 5 (NCLEX regression)
