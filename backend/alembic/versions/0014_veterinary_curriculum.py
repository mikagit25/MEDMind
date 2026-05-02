"""Veterinary curriculum — specialties, modules, lessons with FSM cases.

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

# Deterministic UUIDs so migration is idempotent
def _uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"medmind.vet.0014.{name}"))


VET_SPECIALTIES = [
    {
        "id": _uuid("specialty.small_animal"),
        "name": "Small Animal Medicine",
        "description": "Canine and feline internal medicine, pharmacology, and clinical approach",
        "slug": "small-animal-medicine",
        "is_veterinary": True,
        "is_active": True,
        "icon": "🐕",
    },
    {
        "id": _uuid("specialty.equine"),
        "name": "Equine Medicine",
        "description": "Horse medicine, colic management, and large animal pharmacology",
        "slug": "equine-medicine",
        "is_veterinary": True,
        "is_active": True,
        "icon": "🐎",
    },
    {
        "id": _uuid("specialty.vet_pharmacology"),
        "name": "Veterinary Pharmacology",
        "description": "Species-specific drug metabolism, dosing, toxicology, and antimicrobial stewardship",
        "slug": "veterinary-pharmacology",
        "is_veterinary": True,
        "is_active": True,
        "icon": "💊",
    },
    {
        "id": _uuid("specialty.zoonoses"),
        "name": "Zoonotic Diseases",
        "description": "Diseases transmissible between animals and humans — epidemiology and prevention",
        "slug": "zoonotic-diseases",
        "is_veterinary": True,
        "is_active": True,
        "icon": "🦠",
    },
]

VET_MODULES = [
    # Small Animal
    {
        "id": _uuid("module.feline_ckd"),
        "specialty_id": _uuid("specialty.small_animal"),
        "name": "Feline Chronic Kidney Disease",
        "description": "IRIS staging, management, and renal pharmacology in cats",
        "module_order": 1,
        "is_published": True,
        "is_fundamental": False,
    },
    {
        "id": _uuid("module.canine_endo"),
        "specialty_id": _uuid("specialty.small_animal"),
        "name": "Canine Endocrinology",
        "description": "Diabetes mellitus, hypothyroidism, and Addison's disease in dogs",
        "module_order": 2,
        "is_published": True,
        "is_fundamental": False,
    },
    # Equine
    {
        "id": _uuid("module.equine_colic"),
        "specialty_id": _uuid("specialty.equine"),
        "name": "Equine Colic",
        "description": "Differential diagnosis and medical vs surgical triage of colic",
        "module_order": 1,
        "is_published": True,
        "is_fundamental": False,
    },
    {
        "id": _uuid("module.equine_laminitis"),
        "specialty_id": _uuid("specialty.equine"),
        "name": "Laminitis and Metabolic Disease",
        "description": "Pathophysiology, management, and PPID (equine Cushing's)",
        "module_order": 2,
        "is_published": True,
        "is_fundamental": False,
    },
    # Vet pharmacology
    {
        "id": _uuid("module.feline_drug_metabolism"),
        "specialty_id": _uuid("specialty.vet_pharmacology"),
        "name": "Feline Drug Metabolism",
        "description": "Glucuronidation deficiency and safe analgesic alternatives in cats",
        "module_order": 1,
        "is_published": True,
        "is_fundamental": True,
    },
    {
        "id": _uuid("module.canine_toxins"),
        "specialty_id": _uuid("specialty.vet_pharmacology"),
        "name": "Canine Toxicology",
        "description": "Common household toxins: xylitol, grapes, chocolate, NSAIDs",
        "module_order": 2,
        "is_published": True,
        "is_fundamental": True,
    },
    # Zoonoses
    {
        "id": _uuid("module.zoonoses_core"),
        "specialty_id": _uuid("specialty.zoonoses"),
        "name": "Core Zoonotic Diseases",
        "description": "Rabies, leptospirosis, toxoplasmosis, brucellosis, Q fever",
        "module_order": 1,
        "is_published": True,
        "is_fundamental": True,
    },
    {
        "id": _uuid("module.one_health"),
        "specialty_id": _uuid("specialty.zoonoses"),
        "name": "One Health Approach",
        "description": "Human-animal-environment interface in disease prevention",
        "module_order": 2,
        "is_published": True,
        "is_fundamental": False,
    },
]

VET_LESSONS = [
    # Feline CKD
    {
        "id": _uuid("lesson.feline_ckd_staging"),
        "module_id": _uuid("module.feline_ckd"),
        "title": "IRIS Staging of Feline CKD",
        "lesson_order": 1,
        "is_published": True,
        "content_blocks": [
            {
                "type": "text",
                "content": (
                    "# Feline Chronic Kidney Disease — IRIS Staging\n\n"
                    "CKD is the most common cause of morbidity and mortality in cats over 7 years. "
                    "The International Renal Interest Society (IRIS) staging system is the global standard.\n\n"
                    "## IRIS Stages (based on creatinine)\n"
                    "| Stage | Creatinine (µmol/L) | SDMA (µg/dL) | Clinical Signs |\n"
                    "|-------|---------------------|--------------|----------------|\n"
                    "| 1     | < 140               | < 18         | Non-azotaemic, other markers |\n"
                    "| 2     | 140–249             | 18–25        | Mild azotaemia, PU/PD begins |\n"
                    "| 3     | 250–439             | 26–38        | Moderate — vomiting, weight loss |\n"
                    "| 4     | > 440               | > 38         | Severe — uraemic crisis |\n\n"
                    "## Substaging\n"
                    "- **Proteinuria**: UPC < 0.2 (non-proteinuric), 0.2–0.4 (borderline), > 0.4 (proteinuric)\n"
                    "- **Blood pressure**: < 140 (normotensive) → > 180 mmHg (hypertensive — amlodipine 0.625 mg/cat SID)\n\n"
                    "## Key Management Points\n"
                    "- Phosphate restriction diet (stages 2–4)\n"
                    "- Phosphate binders (aluminium hydroxide, lanthanum carbonate)\n"
                    "- Darbepoetin alfa for non-regenerative anaemia (stage 3–4)\n"
                    "- **Avoid NSAIDs** — cats have limited glucuronidation and pre-existing renal impairment worsens toxicity\n"
                    "- ACE inhibitors (benazepril) for proteinuric cats\n"
                    "- Buprenorphine (0.02 mg/kg OTM) is the preferred analgesic in CKD cats\n"
                )
            },
            {
                "type": "mcq",
                "question": "A 12-year-old DSH cat has creatinine 310 µmol/L, UPC 0.45, and BP 175 mmHg. What is the IRIS classification?",
                "options": [
                    "Stage 2, non-proteinuric, normotensive",
                    "Stage 3, proteinuric, pre-hypertensive",
                    "Stage 3, proteinuric, hypertensive",
                    "Stage 4, borderline proteinuric, hypertensive",
                ],
                "correct": "Stage 3, proteinuric, hypertensive",
                "explanation": "Creatinine 310 = Stage 3 (250–439). UPC 0.45 = proteinuric (>0.4). BP 175 = hypertensive (160–179). This cat needs amlodipine + ACE inhibitor + phosphate restriction."
            },
        ],
    },
    # Equine Colic
    {
        "id": _uuid("lesson.equine_colic_triage"),
        "module_id": _uuid("module.equine_colic"),
        "title": "Colic Triage — Medical vs Surgical",
        "lesson_order": 1,
        "is_published": True,
        "content_blocks": [
            {
                "type": "text",
                "content": (
                    "# Equine Colic — Triage Decision\n\n"
                    "Colic is the leading cause of equine mortality. "
                    "The critical decision is **medical vs surgical management**.\n\n"
                    "## Initial Assessment Parameters\n"
                    "| Parameter | Normal | Medical Colic | Surgical Colic |\n"
                    "|-----------|--------|---------------|----------------|\n"
                    "| HR | 28–44 bpm | 44–60 bpm | > 60 bpm |\n"
                    "| Gut sounds | All quadrants | Reduced | Absent |\n"
                    "| Pain response to analgesia | N/A | Responds | Unresponsive |\n"
                    "| Mucous membranes | Pink, moist | Pale pink | Pale/grey, dry |\n"
                    "| CRT | < 2s | 2–3s | > 3s |\n"
                    "| Reflux > 2L | None | Occasional | Common |\n\n"
                    "## Surgical Colic — Red Flags\n"
                    "- HR > 60 bpm not responding to butorphanol + flunixin\n"
                    "- > 2L nasogastric reflux on repeat passage\n"
                    "- Absent gut sounds in all quadrants\n"
                    "- Pain unresponsive to adequate analgesia\n"
                    "- Deviated loops on rectal or ultrasound\n\n"
                    "## Analgesic Ladder (equine)\n"
                    "1. **Flunixin meglumine** 1.1 mg/kg IV — NSAID, first-line\n"
                    "2. **Butorphanol** 0.02–0.1 mg/kg IV — opioid, additive effect\n"
                    "3. **Detomidine** 10–40 µg/kg IV/IM — α2-agonist for severe pain\n"
                    "4. **Romifidine + butorphanol** IV CRI — continuous for pre-surgical stabilisation\n\n"
                    "⚠️ Avoid high-dose flunixin in horses with suspected mucosal ischaemia — masks clinical signs."
                )
            },
            {
                "type": "mcq",
                "question": "A 6-year-old Thoroughbred gelding presents with colic. HR 72 bpm, absent gut sounds, 3.5L nasogastric reflux, grey mucous membranes, CRT 4s. He did not respond to flunixin + butorphanol. What is the next step?",
                "options": [
                    "Repeat dose of flunixin and reassess in 30 minutes",
                    "Add detomidine and continue medical management",
                    "Refer immediately for surgical colic workup",
                    "Administer mineral oil via nasogastric tube",
                ],
                "correct": "Refer immediately for surgical colic workup",
                "explanation": "This horse has multiple red flags: HR >60, >2L reflux, absent gut sounds, grey MMs, CRT >3s, and failure to respond to analgesia. These indicate a surgical lesion (strangulating obstruction). Immediate referral is mandatory — further medical management risks fatal delay."
            },
        ],
    },
    # Feline drug metabolism
    {
        "id": _uuid("lesson.feline_drug_metabolism"),
        "module_id": _uuid("module.feline_drug_metabolism"),
        "title": "Why Cats Are Different — Glucuronidation and Drug Safety",
        "lesson_order": 1,
        "is_published": True,
        "content_blocks": [
            {
                "type": "text",
                "content": (
                    "# Feline Drug Metabolism — The Glucuronidation Problem\n\n"
                    "Cats are obligate carnivores that evolved on a low-carbohydrate, high-protein diet. "
                    "This has profound consequences for drug metabolism.\n\n"
                    "## The Core Problem\n"
                    "Cats have **deficient hepatic glucuronyl transferase (UGT)** activity — the enzyme responsible "
                    "for glucuronidation (Phase II conjugation). Many drugs that are safe in dogs and humans "
                    "are highly toxic or fatal in cats.\n\n"
                    "## Drugs That Are Dangerous in Cats\n"
                    "| Drug | Risk | Mechanism |\n"
                    "|------|------|----------|\n"
                    "| Paracetamol | FATAL | Glucuronidation-dependent metabolism → toxic NAPQI accumulates → methaemoglobinaemia |\n"
                    "| Aspirin | Toxic (q72h max) | Slow salicylate elimination |\n"
                    "| Ibuprofen | Highly toxic | GI ulceration + acute renal failure |\n"
                    "| Permethrin | FATAL | Neurological — severe tremors/seizures |\n"
                    "| Benzyl alcohol | Fatal | CNS toxicity |\n\n"
                    "## Safe Analgesics in Cats\n"
                    "- **Buprenorphine** 0.02 mg/kg OTM (oral transmucosal) — gold standard\n"
                    "- **Meloxicam** 0.05–0.1 mg/kg SC/oral (short-term only, lowest effective dose)\n"
                    "- **Robenacoxib** — licensed NSAID with short tissue half-life\n"
                    "- **Gabapentin** 5–10 mg/kg PO — neuropathic pain, pre-operative\n\n"
                    "## Paracetamol Toxicity Treatment\n"
                    "Immediately give **N-acetylcysteine** (140 mg/kg IV loading, then 70 mg/kg q4h × 5) "
                    "+ ascorbic acid + oxygen. Prognosis is grave once clinical signs appear."
                )
            },
            {
                "type": "mcq",
                "question": "An owner calls saying they gave their cat one tablet of paracetamol 500mg for pain 1 hour ago. The cat is now showing facial swelling and brown mucous membranes. What do you do FIRST?",
                "options": [
                    "Advise monitoring at home — one tablet is unlikely to be fatal",
                    "Tell the owner to induce vomiting at home with hydrogen peroxide",
                    "Instruct immediate emergency attendance and prepare N-acetylcysteine",
                    "Prescribe liquid antacid to protect the stomach",
                ],
                "correct": "Instruct immediate emergency attendance and prepare N-acetylcysteine",
                "explanation": "Brown MMs = methaemoglobinaemia — paracetamol toxicity is confirmed and progressing. Facial swelling is also a sign. Paracetamol is potentially FATAL in cats. N-acetylcysteine must be given immediately. Inducing emesis is contraindicated once clinical signs are present. Every minute matters."
            },
        ],
    },
    # Canine toxins
    {
        "id": _uuid("lesson.canine_toxins"),
        "module_id": _uuid("module.canine_toxins"),
        "title": "Common Household Toxins in Dogs",
        "lesson_order": 1,
        "is_published": True,
        "content_blocks": [
            {
                "type": "text",
                "content": (
                    "# Canine Toxicology — Common Household Toxins\n\n"
                    "Dogs are indiscriminate eaters. The following toxins are among the most commonly reported "
                    "to poison control centres worldwide.\n\n"
                    "## Xylitol (Sugar-free products)\n"
                    "- **Sources**: sugar-free gum, peanut butter, sweets, some medications\n"
                    "- **Mechanism**: stimulates insulin release → profound hypoglycaemia; high doses cause hepatic necrosis\n"
                    "- **Toxic dose**: 0.1 g/kg (hypoglycaemia); > 0.5 g/kg (liver failure)\n"
                    "- **Treatment**: IV dextrose + hepatoprotectants; no specific antidote for liver failure\n\n"
                    "## Grapes and Raisins\n"
                    "- **Toxic dose**: unknown — idiosyncratic, no safe threshold established\n"
                    "- **Mechanism**: acute renal failure (mechanism not fully elucidated)\n"
                    "- **Signs**: vomiting within hours, then oliguric ARF within 24–72h\n"
                    "- **Treatment**: decontamination, IV fluids, renal monitoring\n\n"
                    "## Chocolate (Methylxanthines)\n"
                    "- **Toxic compounds**: theobromine + caffeine\n"
                    "- **Toxic dose**: > 20 mg/kg theobromine → cardiac/neurological signs\n"
                    "- Dark chocolate: ~150 mg/g; milk: ~15 mg/g; white: negligible\n"
                    "- **Signs**: vomiting, tachycardia, tremors, seizures\n"
                    "- **Treatment**: emesis if < 2h, activated charcoal, supportive\n\n"
                    "## NSAIDs (Human)\n"
                    "- Ibuprofen and naproxen are highly toxic in dogs even at low doses\n"
                    "- GI ulceration, acute renal failure, CNS signs\n"
                    "- **Never** give human NSAIDs to dogs without veterinary guidance\n\n"
                    "## ASPCA Poison Control: +1-888-426-4435"
                )
            },
            {
                "type": "mcq",
                "question": "A 10 kg Labrador ate approximately 50g of dark chocolate (theobromine ~150 mg/g). Total theobromine ingested ≈ 7,500 mg = 750 mg/kg. What is the expected clinical picture?",
                "options": [
                    "Mild GI upset only — 750 mg/kg is below the toxic threshold",
                    "Severe toxicity — tachyarrhythmia, muscle tremors, risk of seizures",
                    "Hepatotoxicity only — chocolate does not cause cardiac signs",
                    "No treatment needed if the dog vomited spontaneously",
                ],
                "correct": "Severe toxicity — tachyarrhythmia, muscle tremors, risk of seizures",
                "explanation": "750 mg/kg is massively above the 20 mg/kg threshold. Expect vomiting, tachycardia, tremors, and possible seizures/death. Immediate decontamination (emesis if < 2h) + activated charcoal + IV access + ECG monitoring. This is a genuine emergency."
            },
        ],
    },
]


def upgrade():
    conn = op.get_bind()

    # Insert specialties
    for sp in VET_SPECIALTIES:
        conn.execute(
            sa.text("""
                INSERT INTO specialties (id, name, description, slug, is_veterinary, is_active)
                VALUES (:id, :name, :description, :slug, :is_veterinary, :is_active)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_veterinary = EXCLUDED.is_veterinary
            """),
            {
                "id": sp["id"],
                "name": sp["name"],
                "description": sp["description"],
                "slug": sp["slug"],
                "is_veterinary": sp["is_veterinary"],
                "is_active": sp["is_active"],
            }
        )

    # Insert modules
    for mod in VET_MODULES:
        conn.execute(
            sa.text("""
                INSERT INTO modules (id, specialty_id, name, description, module_order, is_published, is_fundamental)
                VALUES (:id, :specialty_id, :name, :description, :module_order, :is_published, :is_fundamental)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_published = EXCLUDED.is_published
            """),
            mod,
        )

    # Insert lessons
    for lesson in VET_LESSONS:
        import json as _json
        conn.execute(
            sa.text("""
                INSERT INTO lessons (id, module_id, title, lesson_order, is_published, content_blocks)
                VALUES (:id, :module_id, :title, :lesson_order, :is_published, :content_blocks::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content_blocks = EXCLUDED.content_blocks,
                    is_published = EXCLUDED.is_published
            """),
            {
                "id": lesson["id"],
                "module_id": lesson["module_id"],
                "title": lesson["title"],
                "lesson_order": lesson["lesson_order"],
                "is_published": lesson["is_published"],
                "content_blocks": _json.dumps(lesson["content_blocks"]),
            }
        )


def downgrade():
    conn = op.get_bind()
    # Remove lessons
    for lesson in VET_LESSONS:
        conn.execute(sa.text("DELETE FROM lessons WHERE id = :id"), {"id": lesson["id"]})
    # Remove modules
    for mod in VET_MODULES:
        conn.execute(sa.text("DELETE FROM modules WHERE id = :id"), {"id": mod["id"]})
    # Remove specialties
    for sp in VET_SPECIALTIES:
        conn.execute(sa.text("DELETE FROM specialties WHERE id = :id"), {"id": sp["id"]})
