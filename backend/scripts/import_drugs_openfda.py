"""
OpenFDA Drug Import Script
==========================
Fetches structured drug label data from the US FDA and populates the `drugs` table.

Sources:
  - OpenFDA Drug Labels API  (labels, indications, AEs, black-box warnings)
  - RxNorm API               (drug class via ATC/MeSH pharmacological class)

Usage (from backend/):
    python -m scripts.import_drugs_openfda                  # import all ~250 high-yield drugs
    python -m scripts.import_drugs_openfda --class Statins  # only one class
    python -m scripts.import_drugs_openfda --limit 20       # first N drugs
    python -m scripts.import_drugs_openfda --dry-run        # parse only, no DB writes
    python -m scripts.import_drugs_openfda --update-only    # skip drugs already in DB

Idempotent: re-running updates existing records, never duplicates.
Rate limit: OpenFDA allows 240 req/min without API key; we use ~30 req/min to be safe.
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── High-yield drug list ──────────────────────────────────────────────────────
# ~250 drugs organised by pharmacological class.
# The key becomes drug_class in DB; values are generic names sent to OpenFDA.

HIGH_YIELD_DRUGS: dict[str, list[str]] = {
    "ACE Inhibitors": [
        "lisinopril", "enalapril", "ramipril", "captopril", "benazepril", "fosinopril",
    ],
    "Angiotensin Receptor Blockers": [
        "losartan", "valsartan", "irbesartan", "olmesartan", "candesartan", "telmisartan",
    ],
    "Beta Blockers": [
        "metoprolol", "atenolol", "carvedilol", "propranolol", "bisoprolol",
        "labetalol", "nebivolol",
    ],
    "Calcium Channel Blockers": [
        "amlodipine", "nifedipine", "diltiazem", "verapamil", "felodipine",
    ],
    "Loop Diuretics": [
        "furosemide", "bumetanide", "torsemide",
    ],
    "Thiazide Diuretics": [
        "hydrochlorothiazide", "chlorthalidone", "metolazone",
    ],
    "Potassium-sparing Diuretics": [
        "spironolactone", "eplerenone", "amiloride", "triamterene",
    ],
    "Statins": [
        "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
        "lovastatin", "pitavastatin",
    ],
    "Antiplatelet Agents": [
        "aspirin", "clopidogrel", "ticagrelor", "prasugrel", "ticlopidine",
    ],
    "Anticoagulants": [
        "warfarin", "heparin", "enoxaparin", "rivaroxaban",
        "apixaban", "dabigatran", "fondaparinux",
    ],
    "Nitrates": [
        "nitroglycerin", "isosorbide mononitrate", "isosorbide dinitrate",
    ],
    "Antiarrhythmics": [
        "amiodarone", "digoxin", "sotalol", "flecainide",
        "adenosine", "lidocaine", "mexiletine",
    ],
    "Penicillins": [
        "amoxicillin", "ampicillin", "nafcillin", "dicloxacillin",
        "piperacillin", "amoxicillin-clavulanate",
    ],
    "Cephalosporins": [
        "cephalexin", "cefazolin", "cefuroxime", "ceftriaxone",
        "cefepime", "ceftazidime", "ceftaroline",
    ],
    "Macrolides": [
        "azithromycin", "clarithromycin", "erythromycin",
    ],
    "Fluoroquinolones": [
        "ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin",
    ],
    "Aminoglycosides": [
        "gentamicin", "tobramycin", "amikacin", "streptomycin",
    ],
    "Carbapenems": [
        "meropenem", "imipenem-cilastatin", "ertapenem", "doripenem",
    ],
    "Glycopeptides": [
        "vancomycin", "teicoplanin",
    ],
    "Tetracyclines": [
        "doxycycline", "minocycline", "tetracycline", "tigecycline",
    ],
    "Oxazolidinones": [
        "linezolid",
    ],
    "Antifungals": [
        "fluconazole", "voriconazole", "itraconazole",
        "amphotericin b", "caspofungin", "micafungin",
    ],
    "Antivirals - Herpesviruses": [
        "acyclovir", "valacyclovir", "famciclovir", "ganciclovir", "valganciclovir",
    ],
    "Antivirals - Influenza": [
        "oseltamivir", "zanamivir", "baloxavir",
    ],
    "Antiretrovirals": [
        "tenofovir", "emtricitabine", "efavirenz",
        "dolutegravir", "ritonavir", "atazanavir",
    ],
    "SSRIs": [
        "fluoxetine", "sertraline", "escitalopram",
        "paroxetine", "fluvoxamine", "citalopram",
    ],
    "SNRIs": [
        "venlafaxine", "duloxetine", "desvenlafaxine", "levomilnacipran",
    ],
    "Tricyclic Antidepressants": [
        "amitriptyline", "nortriptyline", "imipramine", "clomipramine",
    ],
    "Atypical Antidepressants": [
        "bupropion", "mirtazapine", "trazodone",
    ],
    "Antipsychotics - Typical": [
        "haloperidol", "chlorpromazine", "fluphenazine",
    ],
    "Antipsychotics - Atypical": [
        "risperidone", "olanzapine", "quetiapine",
        "clozapine", "aripiprazole", "ziprasidone", "lurasidone",
    ],
    "Benzodiazepines": [
        "diazepam", "lorazepam", "alprazolam", "midazolam",
        "clonazepam", "temazepam",
    ],
    "Antiepileptics": [
        "phenytoin", "valproate", "carbamazepine",
        "lamotrigine", "levetiracetam", "topiramate",
        "oxcarbazepine", "gabapentin", "pregabalin",
    ],
    "Opioid Analgesics": [
        "morphine", "oxycodone", "hydrocodone", "fentanyl",
        "hydromorphone", "codeine", "tramadol", "buprenorphine",
    ],
    "Opioid Antagonists": [
        "naloxone", "naltrexone",
    ],
    "NSAIDs": [
        "ibuprofen", "naproxen", "indomethacin", "ketorolac",
        "celecoxib", "diclofenac", "meloxicam",
    ],
    "Corticosteroids - Systemic": [
        "prednisone", "methylprednisolone", "dexamethasone",
        "hydrocortisone", "betamethasone",
    ],
    "Proton Pump Inhibitors": [
        "omeprazole", "pantoprazole", "lansoprazole",
        "esomeprazole", "rabeprazole",
    ],
    "H2 Receptor Antagonists": [
        "famotidine", "ranitidine", "cimetidine",
    ],
    "Antiemetics": [
        "ondansetron", "metoclopramide", "promethazine",
        "prochlorperazine", "dexamethasone",
    ],
    "Laxatives": [
        "polyethylene glycol", "lactulose", "bisacodyl", "docusate",
    ],
    "Short-acting Beta2 Agonists": [
        "albuterol", "levalbuterol", "terbutaline",
    ],
    "Long-acting Beta2 Agonists": [
        "salmeterol", "formoterol", "indacaterol",
    ],
    "Anticholinergics - Respiratory": [
        "ipratropium", "tiotropium", "umeclidinium",
    ],
    "Inhaled Corticosteroids": [
        "budesonide", "fluticasone", "beclomethasone", "mometasone",
    ],
    "Methylxanthines": [
        "theophylline", "aminophylline",
    ],
    "Insulins": [
        "insulin glargine", "insulin aspart", "insulin lispro",
        "insulin detemir", "insulin degludec", "regular insulin",
    ],
    "Biguanides": [
        "metformin",
    ],
    "Sulfonylureas": [
        "glipizide", "glyburide", "glimepiride",
    ],
    "DPP-4 Inhibitors": [
        "sitagliptin", "saxagliptin", "linagliptin", "alogliptin",
    ],
    "SGLT2 Inhibitors": [
        "empagliflozin", "dapagliflozin", "canagliflozin",
    ],
    "GLP-1 Receptor Agonists": [
        "liraglutide", "semaglutide", "exenatide", "dulaglutide",
    ],
    "Thiazolidinediones": [
        "pioglitazone", "rosiglitazone",
    ],
    "Thyroid Agents": [
        "levothyroxine", "liothyronine", "methimazole", "propylthiouracil",
    ],
    "Immunosuppressants - Calcineurin Inhibitors": [
        "tacrolimus", "cyclosporine",
    ],
    "Immunosuppressants - Antimetabolites": [
        "mycophenolate", "azathioprine", "methotrexate",
    ],
    "mTOR Inhibitors": [
        "sirolimus", "everolimus",
    ],
    "Monoclonal Antibodies - TNF-alpha": [
        "adalimumab", "infliximab", "etanercept", "certolizumab",
    ],
    "Monoclonal Antibodies - Oncology": [
        "rituximab", "trastuzumab", "bevacizumab", "cetuximab",
    ],
    "Alkylating Agents": [
        "cyclophosphamide", "cisplatin", "carboplatin", "oxaliplatin",
    ],
    "Antimetabolites - Oncology": [
        "methotrexate", "fluorouracil", "gemcitabine", "capecitabine",
    ],
    "Taxanes": [
        "paclitaxel", "docetaxel",
    ],
    "Vinca Alkaloids": [
        "vincristine", "vinblastine",
    ],
    "Anthracyclines": [
        "doxorubicin", "epirubicin", "daunorubicin",
    ],
    "Antihistamines - First Generation": [
        "diphenhydramine", "hydroxyzine", "chlorpheniramine",
    ],
    "Antihistamines - Second Generation": [
        "cetirizine", "loratadine", "fexofenadine", "desloratadine",
    ],
    "Anticholinesterases": [
        "donepezil", "rivastigmine", "galantamine",
    ],
    "Parkinson's - Dopaminergics": [
        "levodopa", "carbidopa-levodopa", "pramipexole",
        "ropinirole", "rotigotine",
    ],
    "Parkinson's - MAO-B Inhibitors": [
        "selegiline", "rasagiline", "safinamide",
    ],
    "Muscle Relaxants": [
        "cyclobenzaprine", "baclofen", "methocarbamol",
        "tizanidine", "carisoprodol",
    ],
    "Bisphosphonates": [
        "alendronate", "risedronate", "zoledronic acid", "ibandronate",
    ],
    "Gout Agents": [
        "colchicine", "allopurinol", "febuxostat", "probenecid",
    ],
    "Antiparasitics": [
        "metronidazole", "albendazole", "mebendazole",
        "ivermectin", "praziquantel", "chloroquine", "hydroxychloroquine",
    ],
    "Antituberculosis": [
        "isoniazid", "rifampin", "pyrazinamide", "ethambutol",
    ],
}

# Drugs with narrow therapeutic index
NTI_DRUGS: set[str] = {
    "warfarin", "digoxin", "phenytoin", "lithium", "theophylline",
    "cyclosporine", "tacrolimus", "carbamazepine", "valproate", "levothyroxine",
    "methotrexate", "aminophylline", "vancomycin", "heparin",
    "gentamicin", "tobramycin", "amikacin", "streptomycin",
    "sirolimus", "everolimus", "cyclosporine",
}

OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
RXNORM_CLASS_URL  = "https://rxnav.nlm.nih.gov/REST/rxclass/class/byDrugName.json"

# ── Text helpers ──────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Remove FDA markup, excessive whitespace."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\(See [^)]+\)", "", text)
    text = re.sub(r"\b\d+\s+DOSAGE AND ADMINISTRATION\b", "", text, flags=re.I)
    return text.strip()


def split_into_list(text: str, max_items: int = 15) -> list[str]:
    """
    Split long FDA text paragraph into list items.
    Tries bullet/number patterns first, then sentence-splits.
    """
    if not text:
        return []

    text = clean_text(text)

    # Try splitting on explicit bullets or numbered lists
    items = re.split(r"(?:\r?\n|\s{2,})(?:\d+[.)]\s+|•\s+|-\s+)", text)
    if len(items) > 2:
        items = [i.strip() for i in items if len(i.strip()) > 10]
        return items[:max_items]

    # Split on sentence boundaries, keep sentences that look like clinical facts
    sentences = re.split(r"(?<=[.;])\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    return sentences[:max_items]


def parse_adverse_effects(raw_text: str) -> dict[str, list[str]]:
    """
    Parse FDA adverse_reactions blob into {category: [effects]} dict.
    Categories: common, serious, rare, other.
    """
    if not raw_text:
        return {}

    text = clean_text(raw_text)
    result: dict[str, list[str]] = {}

    # Find sections by common FDA headers
    sections = {
        "common":   r"(?i)(most common|common adverse|frequently reported|incidence[^:]*:)[^.]*\.?([\s\S]+?)(?=(?:serious|rare|uncommon|less common|\Z))",
        "serious":  r"(?i)(serious adverse|severe|life.threatening)[^.]*\.?([\s\S]+?)(?=(?:common|rare|uncommon|\Z))",
        "rare":     r"(?i)(rare|uncommon|infrequent)[^.]*\.?([\s\S]+?)(?=(?:common|serious|\Z))",
    }

    for category, pattern in sections.items():
        m = re.search(pattern, text)
        if m:
            chunk = m.group(2) if m.lastindex >= 2 else m.group(1)
            # Extract individual effect terms (comma/semicolon separated)
            effects = [e.strip() for e in re.split(r"[,;]", chunk) if 3 < len(e.strip()) < 80]
            if effects:
                result[category] = effects[:15]

    # Fallback: comma-separated list from full text
    if not result:
        items = [e.strip() for e in re.split(r"[,;]", text) if 3 < len(e.strip()) < 80]
        if items:
            result["reported"] = items[:20]

    return result


def parse_dosing(raw_text: str) -> dict[str, str]:
    """
    Extract key dosing info as {route_or_indication: dose_string}.
    """
    if not raw_text:
        return {}

    text = clean_text(raw_text)
    dosing: dict[str, str] = {}

    # Look for route-based patterns: "Oral:", "IV:", "Intravenous:"
    route_pattern = re.compile(
        r"(oral|intravenous|IV\b|intramuscular|IM\b|subcutaneous|SC\b|topical|inhaled?|inhal)"
        r"[:\s]+([^.;]{10,120})",
        re.I,
    )
    for m in route_pattern.finditer(text):
        route = m.group(1).strip().capitalize()
        dose = m.group(2).strip()
        if route not in dosing:
            dosing[route] = dose[:150]

    # Look for adult dose pattern
    adult_m = re.search(r"(?i)(adult[s]?|usual dose)[:\s]+([^.;]{10,120})", text)
    if adult_m and "Adult" not in dosing:
        dosing["Adult (usual)"] = adult_m.group(2).strip()[:150]

    # Fallback: first two sentences
    if not dosing:
        sentences = re.split(r"(?<=[.;])\s+", text)
        if sentences:
            dosing["General"] = sentences[0][:200]

    return dosing


def parse_monitoring(raw_text: str) -> list[str]:
    """Extract monitoring parameters from warnings/precautions text."""
    if not raw_text:
        return []

    text = clean_text(raw_text)
    items = []

    # Look for explicit "monitor" sentences
    for sentence in re.split(r"(?<=[.;])\s+", text):
        if re.search(r"\b(monitor|check|measure|assess|test)\b", sentence, re.I):
            clean = sentence.strip()
            if 15 < len(clean) < 200:
                items.append(clean)
        if len(items) >= 8:
            break

    return items


def parse_indications(raw_text: str) -> list[str]:
    """Parse indications text into a clean list."""
    if not raw_text:
        return []
    text = clean_text(raw_text)
    # Remove the typical FDA preamble
    text = re.sub(
        r"(?i)^\s*\d+\s+INDICATIONS AND USAGE\s*", "", text
    ).strip()
    return split_into_list(text, max_items=10)


def parse_contraindications(raw_text: str) -> list[str]:
    """Parse contraindications text into a clean list."""
    if not raw_text:
        return []
    text = clean_text(raw_text)
    text = re.sub(r"(?i)^\s*\d+\s+CONTRAINDICATIONS\s*", "", text).strip()
    items = split_into_list(text, max_items=10)
    # Filter to lines that read like contraindications
    return [i for i in items if len(i) > 10]


# ── OpenFDA fetcher ───────────────────────────────────────────────────────────

async def fetch_fda_label(client: httpx.AsyncClient, drug_name: str) -> dict[str, Any] | None:
    """Query OpenFDA drug label API for a generic drug name."""
    # Try exact generic name first, then brand name
    queries = [
        f'openfda.generic_name:"{drug_name}"',
        f'openfda.brand_name:"{drug_name}"',
        f'"{drug_name}"',
    ]
    for query in queries:
        try:
            resp = await client.get(
                OPENFDA_LABEL_URL,
                params={"search": query, "limit": 1},
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    return results[0]
            elif resp.status_code == 404:
                continue  # no results for this query form
            else:
                log.warning("OpenFDA returned %s for %s", resp.status_code, drug_name)
        except httpx.RequestError as e:
            log.warning("HTTP error for %s: %s", drug_name, e)
    return None


async def fetch_rxnorm_class(client: httpx.AsyncClient, drug_name: str) -> str | None:
    """Get pharmacological class from RxNorm (EPC class = established pharmacologic class)."""
    try:
        resp = await client.get(
            RXNORM_CLASS_URL,
            params={"drugName": drug_name, "relaSource": "FDASPL"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        classes = (
            data.get("rxclassDrugInfoList", {})
            .get("rxclassDrugInfo", [])
        )
        # Prefer EPC (established pharmacologic class) type
        for c in classes:
            ci = c.get("rxclassMinConceptItem", {})
            if ci.get("classType") in ("EPC", "MOA", "PE"):
                return ci.get("className")
        # Fallback: first class
        if classes:
            return classes[0].get("rxclassMinConceptItem", {}).get("className")
    except Exception:
        pass
    return None


# ── Drug record builder ───────────────────────────────────────────────────────

def build_drug_record(
    drug_name: str,
    drug_class: str,
    label: dict[str, Any],
    rxnorm_class: str | None,
) -> dict[str, Any]:
    """Map OpenFDA label JSON to our Drug schema."""
    openfda = label.get("openfda", {})

    # Resolve names
    brand_names: list[str] = openfda.get("brand_name", [])
    generic_names: list[str] = openfda.get("generic_name", [])
    name = (brand_names[0] if brand_names else drug_name).title()
    generic_name = (generic_names[0] if generic_names else drug_name).title()

    # Drug class: prefer our curated class, enrich with RxNorm if available
    resolved_class = rxnorm_class or drug_class

    # Raw FDA text fields (each is a list of strings in OpenFDA)
    def first(field: str) -> str:
        vals = label.get(field, [])
        return vals[0] if vals else ""

    mechanism_raw       = first("mechanism_of_action") or first("clinical_pharmacology")
    indications_raw     = first("indications_and_usage")
    contraindications_raw = first("contraindications")
    adverse_raw         = first("adverse_reactions")
    dosing_raw          = first("dosage_and_administration")
    warnings_raw        = first("warnings_and_cautions") or first("warnings")
    black_box_raw       = first("boxed_warning")
    interactions_raw    = first("drug_interactions")

    # Parse mechanism: take first paragraph (max 600 chars)
    mechanism = ""
    if mechanism_raw:
        sentences = re.split(r"(?<=[.;])\s+", clean_text(mechanism_raw))
        paras = []
        total = 0
        for s in sentences:
            if total + len(s) > 600:
                break
            paras.append(s)
            total += len(s)
        mechanism = " ".join(paras).strip()

    # Parse interactions: extract drug names / key statements
    interactions: list[str] = []
    if interactions_raw:
        itext = clean_text(interactions_raw)
        for sentence in re.split(r"(?<=[.;])\s+", itext):
            if re.search(r"\b(increases?|decreases?|inhibits?|induces?|potentiates?|additive|contraindicated)\b", sentence, re.I):
                s = sentence.strip()
                if 15 < len(s) < 200:
                    interactions.append(s)
            if len(interactions) >= 10:
                break

    return {
        "name": name,
        "generic_name": generic_name,
        "drug_class": resolved_class,
        "mechanism": mechanism or None,
        "indications": parse_indications(indications_raw),
        "contraindications": parse_contraindications(contraindications_raw),
        "adverse_effects": parse_adverse_effects(adverse_raw),
        "dosing": parse_dosing(dosing_raw),
        "monitoring": parse_monitoring(warnings_raw),
        "black_box_warning": clean_text(black_box_raw)[:1000] if black_box_raw else None,
        "interactions": interactions,
        "is_high_yield": True,
        "is_nti": drug_name.lower() in NTI_DRUGS,
        "is_veterinary": False,
    }


# ── DB upsert ────────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO drugs (
    id, name, generic_name, drug_class, mechanism,
    indications, contraindications, adverse_effects, dosing,
    monitoring, black_box_warning, interactions,
    is_high_yield, is_nti, is_veterinary,
    created_at, updated_at
) VALUES (
    $1, $2, $3, $4, $5,
    $6, $7, $8, $9,
    $10, $11, $12,
    $13, $14, $15,
    NOW(), NOW()
)
ON CONFLICT (lower(name)) DO UPDATE SET
    generic_name     = EXCLUDED.generic_name,
    drug_class       = EXCLUDED.drug_class,
    mechanism        = EXCLUDED.mechanism,
    indications      = EXCLUDED.indications,
    contraindications= EXCLUDED.contraindications,
    adverse_effects  = EXCLUDED.adverse_effects,
    dosing           = EXCLUDED.dosing,
    monitoring       = EXCLUDED.monitoring,
    black_box_warning= EXCLUDED.black_box_warning,
    interactions     = EXCLUDED.interactions,
    is_high_yield    = EXCLUDED.is_high_yield,
    is_nti           = EXCLUDED.is_nti,
    updated_at       = NOW()
RETURNING id, (xmax = 0) AS inserted;
"""


async def upsert_drug(conn: asyncpg.Connection, record: dict[str, Any]) -> tuple[str, bool]:
    """Insert or update a drug record. Returns (id, was_inserted)."""
    row = await conn.fetchrow(
        UPSERT_SQL,
        uuid.uuid4(),
        record["name"],
        record["generic_name"],
        record["drug_class"],
        record["mechanism"],
        record["indications"],
        record["contraindications"],
        json.dumps(record["adverse_effects"]),
        json.dumps(record["dosing"]),
        record["monitoring"],
        record["black_box_warning"],
        record["interactions"],
        record["is_high_yield"],
        record["is_nti"],
        record["is_veterinary"],
    )
    return str(row["id"]), bool(row["inserted"])


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(args: argparse.Namespace) -> None:
    db_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    # Build work list
    work: list[tuple[str, str]] = []  # (drug_name, class_name)
    for class_name, drugs in HIGH_YIELD_DRUGS.items():
        if args.drug_class and class_name.lower() != args.drug_class.lower():
            continue
        for drug_name in drugs:
            work.append((drug_name, class_name))

    if args.limit:
        work = work[: args.limit]

    log.info("Importing %d drugs (dry_run=%s, update_only=%s)", len(work), args.dry_run, args.update_only)

    conn: asyncpg.Connection | None = None
    if not args.dry_run:
        conn = await asyncpg.connect(db_url)
        # Ensure name unique index exists (idempotent)
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_drugs_name ON drugs (LOWER(name));"
        )

    stats = {"inserted": 0, "updated": 0, "skipped": 0, "not_found": 0, "error": 0}

    async with httpx.AsyncClient(
        headers={"User-Agent": "MedMind-Importer/1.0 (educational)"},
        follow_redirects=True,
    ) as client:
        for i, (drug_name, drug_class) in enumerate(work, 1):
            log.info("[%d/%d] %s (%s)", i, len(work), drug_name, drug_class)

            # Skip if already in DB and --update-only not set
            if args.update_only and conn:
                exists = await conn.fetchval(
                    "SELECT 1 FROM drugs WHERE LOWER(name) = LOWER($1) LIMIT 1", drug_name
                )
                if exists:
                    log.info("  → skip (already in DB)")
                    stats["skipped"] += 1
                    continue

            # Fetch label from OpenFDA
            try:
                label = await fetch_fda_label(client, drug_name)
            except Exception as e:
                log.error("  → fetch error: %s", e)
                stats["error"] += 1
                continue

            if not label:
                log.warning("  → not found in OpenFDA")
                stats["not_found"] += 1
                continue

            # Optionally enrich with RxNorm class
            rxnorm_class = None
            if not args.no_rxnorm:
                try:
                    rxnorm_class = await fetch_rxnorm_class(client, drug_name)
                except Exception:
                    pass

            # Build record
            try:
                record = build_drug_record(drug_name, drug_class, label, rxnorm_class)
            except Exception as e:
                log.error("  → parse error: %s", e)
                stats["error"] += 1
                continue

            if args.dry_run:
                print(json.dumps(record, indent=2, ensure_ascii=False))
                stats["inserted"] += 1
            else:
                try:
                    _, inserted = await upsert_drug(conn, record)
                    if inserted:
                        log.info("  → inserted  [%s]", record["name"])
                        stats["inserted"] += 1
                    else:
                        log.info("  → updated   [%s]", record["name"])
                        stats["updated"] += 1
                except Exception as e:
                    log.error("  → DB error: %s", e)
                    stats["error"] += 1

            # Rate limiting: ~30 req/min (OpenFDA limit is 240/min without key)
            await asyncio.sleep(2.0)

    if conn:
        await conn.close()

    total = await _db_count(db_url) if not args.dry_run else "—"
    log.info(
        "Done. inserted=%d  updated=%d  skipped=%d  not_found=%d  errors=%d  total_in_db=%s",
        stats["inserted"], stats["updated"], stats["skipped"],
        stats["not_found"], stats["error"], total,
    )


async def _db_count(db_url: str) -> int:
    conn = await asyncpg.connect(db_url)
    count = await conn.fetchval("SELECT COUNT(*) FROM drugs")
    await conn.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import drugs from OpenFDA into MedMind DB")
    parser.add_argument("--class", dest="drug_class", metavar="CLASS",
                        help="Import only this drug class (exact match)")
    parser.add_argument("--limit", type=int, metavar="N",
                        help="Import at most N drugs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print parsed records, do not write to DB")
    parser.add_argument("--update-only", action="store_true",
                        help="Skip drugs already present in DB")
    parser.add_argument("--no-rxnorm", action="store_true",
                        help="Skip RxNorm class enrichment (faster)")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
