"""Veterinary mode routes."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User
from app.services.vet_service import (
    get_all_species,
    get_dosing_for_drug_species,
    check_species_safety,
)

router = APIRouter(prefix="/veterinary", tags=["veterinary"])


class SpeciesOut(BaseModel):
    id: UUID
    name: str
    name_ru: str | None
    scientific_name: str | None
    category: str | None
    icon: str | None

    model_config = {"from_attributes": True}


class DosingOut(BaseModel):
    route: str | None
    dose: str | None
    frequency: str | None
    max_dose: str | None
    is_toxic: bool
    toxicity_note: str | None
    notes: str | None
    source: str | None

    model_config = {"from_attributes": True}


class SafetyCheckRequest(BaseModel):
    drug_id: UUID
    species_id: UUID


@router.get("/species", response_model=list[SpeciesOut])
async def list_species(db: AsyncSession = Depends(get_db)):
    """List all animal species available in veterinary mode."""
    return await get_all_species(db)


@router.get("/drugs/{drug_id}/dosing/{species_id}", response_model=list[DosingOut])
async def get_drug_dosing(
    drug_id: UUID,
    species_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get species-specific dosing for a drug."""
    entries = await get_dosing_for_drug_species(db, drug_id, species_id)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail="No dosing information found for this drug/species combination.",
        )
    return entries


@router.post("/drugs/check-species-safety")
async def check_drug_species_safety(
    data: SafetyCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check if a drug is safe for a given animal species."""
    return await check_species_safety(db, data.drug_id, data.species_id)


@router.get("/zoonoses")
async def get_zoonoses(user: User = Depends(get_current_user)):
    """List common zoonotic diseases (educational reference)."""
    return {
        "zoonoses": [
            {
                "name": "Rabies",
                "name_ru": "Бешенство",
                "pathogen": "Lyssavirus",
                "transmission": "Bite from infected animal, saliva contact with mucosa",
                "species": ["Dog", "Cat", "Bat", "Fox", "Raccoon", "Wolf"],
                "prevention": "Pre-/post-exposure prophylaxis, animal vaccination",
                "incubation": "2–12 weeks (up to 1 year)",
                "human_risk": "HIGH — virtually 100% fatal once symptomatic",
            },
            {
                "name": "Leptospirosis",
                "name_ru": "Лептоспироз",
                "pathogen": "Leptospira interrogans",
                "transmission": "Contact with infected urine, contaminated soil or water",
                "species": ["Rat", "Dog", "Cattle", "Pig", "Horse"],
                "prevention": "Vaccination (dogs), avoid contaminated water, protective footwear",
                "incubation": "2–30 days",
                "human_risk": "MODERATE — Weil's disease in ~10% (hepatorenal syndrome)",
            },
            {
                "name": "Toxoplasmosis",
                "name_ru": "Токсоплазмоз",
                "pathogen": "Toxoplasma gondii",
                "transmission": "Cat feces (oocysts), undercooked meat, transplacental",
                "species": ["Cat (definitive host)", "Sheep", "Pig"],
                "prevention": "Litter hygiene, avoid raw meat, gloves for gardening",
                "incubation": "5–23 days",
                "human_risk": "HIGH in immunosuppressed and pregnant women",
            },
            {
                "name": "Brucellosis",
                "name_ru": "Бруцеллёз",
                "pathogen": "Brucella spp. (B. abortus, B. melitensis, B. canis)",
                "transmission": "Contact with infected animals, abortive material, unpasteurized dairy",
                "species": ["Cattle", "Dog", "Sheep", "Goat", "Pig"],
                "prevention": "Pasteurization, animal vaccination, protective equipment",
                "incubation": "1–4 weeks",
                "human_risk": "MODERATE — undulant fever, orchitis, spondylitis",
            },
            {
                "name": "Q Fever",
                "name_ru": "Лихорадка Ку",
                "pathogen": "Coxiella burnetii",
                "transmission": "Inhaled aerosols from birthing fluids, wool, placenta",
                "species": ["Sheep", "Cattle", "Cat", "Goat"],
                "prevention": "Protective equipment, avoid birthing areas, vaccination (endemic areas)",
                "incubation": "2–3 weeks",
                "human_risk": "MODERATE — chronic form causes endocarditis",
            },
            {
                "name": "Salmonellosis",
                "name_ru": "Сальмонеллёз",
                "pathogen": "Salmonella enterica",
                "transmission": "Fecal-oral from reptiles, poultry, contaminated food",
                "species": ["Reptiles", "Poultry", "Cattle", "Pig", "Dog", "Cat"],
                "prevention": "Hand hygiene after animal contact, cook meat thoroughly",
                "incubation": "6–72 hours",
                "human_risk": "HIGH frequency; severe in immunocompromised",
            },
            {
                "name": "Campylobacteriosis",
                "name_ru": "Кампилобактериоз",
                "pathogen": "Campylobacter jejuni/coli",
                "transmission": "Contact with infected animals, undercooked poultry, contaminated water",
                "species": ["Poultry", "Dog", "Cat", "Cattle"],
                "prevention": "Cook poultry thoroughly, hand hygiene",
                "incubation": "2–5 days",
                "human_risk": "HIGH frequency — leading cause of bacterial gastroenteritis",
            },
            {
                "name": "Cat Scratch Disease",
                "name_ru": "Болезнь кошачьих царапин",
                "pathogen": "Bartonella henselae",
                "transmission": "Scratch or bite from infected cat (kitten fleas as vector)",
                "species": ["Cat (especially kittens)"],
                "prevention": "Avoid rough play with kittens, flea control",
                "incubation": "3–14 days",
                "human_risk": "LOW in immunocompetent; HIGH in HIV — bacillary angiomatosis",
            },
            {
                "name": "Psittacosis (Ornithosis)",
                "name_ru": "Пситтакоз",
                "pathogen": "Chlamydophila psittaci",
                "transmission": "Inhaled dried bird feces or respiratory secretions",
                "species": ["Parrots", "Pigeons", "Ducks", "Poultry"],
                "prevention": "Respiratory protection, proper ventilation, quarantine new birds",
                "incubation": "5–14 days",
                "human_risk": "MODERATE — atypical pneumonia, hepatitis",
            },
            {
                "name": "Ringworm (Dermatophytosis)",
                "name_ru": "Стригущий лишай",
                "pathogen": "Microsporum canis, Trichophyton spp.",
                "transmission": "Direct skin contact with infected animal or contaminated fomites",
                "species": ["Cat", "Dog", "Cattle", "Horse"],
                "prevention": "Treat infected animals, wash hands, disinfect surfaces",
                "incubation": "4–14 days",
                "human_risk": "LOW — superficial, treatable; commonest in children",
            },
            {
                "name": "Cryptosporidiosis",
                "name_ru": "Криптоспоридиоз",
                "pathogen": "Cryptosporidium parvum",
                "transmission": "Fecal-oral; calves, lambs, contaminated water",
                "species": ["Cattle (calves)", "Sheep (lambs)", "Cat", "Dog"],
                "prevention": "Water treatment, hygiene, avoid contact with neonatal ruminants",
                "incubation": "1–12 days",
                "human_risk": "HIGH in immunocompromised (AIDS) — severe, prolonged diarrhea",
            },
            {
                "name": "Monkeypox (Mpox)",
                "name_ru": "Оспа обезьян",
                "pathogen": "Monkeypox virus (Orthopoxvirus)",
                "transmission": "Contact with infected rodents, primates; skin lesions, respiratory",
                "species": ["Rodents (prairie dogs, rope squirrels)", "Primates", "Rabbits"],
                "prevention": "Smallpox vaccine, avoid contact with wild rodents, isolation of cases",
                "incubation": "5–21 days",
                "human_risk": "MODERATE — vesicular rash, lymphadenopathy",
            },
            {
                "name": "Echinococcosis (Hydatid Disease)",
                "name_ru": "Эхинококкоз",
                "pathogen": "Echinococcus granulosus / E. multilocularis",
                "transmission": "Ingestion of eggs from dog feces, contaminated food/water",
                "species": ["Dog (definitive)", "Sheep", "Cattle (intermediate hosts)"],
                "prevention": "Deworm dogs regularly, proper meat inspection, hygiene",
                "incubation": "Years (slow-growing cysts)",
                "human_risk": "HIGH — liver/lung cysts, surgical emergency if rupture",
            },
            {
                "name": "Avian Influenza (H5N1/H7N9)",
                "name_ru": "Птичий грипп",
                "pathogen": "Influenza A (H5N1, H7N9)",
                "transmission": "Direct contact with infected poultry, contaminated surfaces",
                "species": ["Poultry (chickens, ducks)", "Wild birds"],
                "prevention": "Avoid contact with sick birds, protective equipment, surveillance",
                "incubation": "2–5 days",
                "human_risk": "HIGH mortality (~60% for H5N1) but limited human-to-human spread",
            },
            {
                "name": "Cowpox / Orf",
                "name_ru": "Коровья оспа / Орф",
                "pathogen": "Cowpox virus / Parapoxvirus",
                "transmission": "Direct contact with lesions (cattle, cats, sheep)",
                "species": ["Cattle", "Cat", "Sheep", "Goat"],
                "prevention": "Protective gloves, wound hygiene",
                "incubation": "5–7 days",
                "human_risk": "LOW — localized skin lesion, self-limiting",
            },
        ]
    }


_CLINICAL_PEARLS = [
    # Pharmacology
    {"species": "Cat", "category": "Pharmacology", "pearl": "Cats lack hepatic glucuronyl transferase (UGT1A6/1A9). Paracetamol/acetaminophen causes fatal methaemoglobinaemia and acute hepatic necrosis — ABSOLUTELY CONTRAINDICATED, even one tablet can be fatal.", "source": "Plumb's Veterinary Drug Handbook"},
    {"species": "Cat", "category": "Pharmacology", "pearl": "Aspirin in cats: extremely long half-life (~40h vs. ~8h in dogs) due to glucuronidation deficiency. If used at all, maximum q72h. Most NSAIDs are contraindicated.", "source": "Maddison et al., Small Animal Clinical Pharmacology"},
    {"species": "Dog", "category": "Pharmacology", "pearl": "Xylitol (E967, common in sugar-free gum, peanut butter, baked goods) causes rapid, severe hypoglycaemia within 30 min and potentially fatal acute liver failure. ~0.1 g/kg triggers hypoglycaemia; >0.5 g/kg causes liver necrosis.", "source": "ASPCA Animal Poison Control"},
    {"species": "Dog", "category": "Pharmacology", "pearl": "MDR1 (ABCB1) gene mutation in Collies, Shelties, Australian Shepherds, and Border Collies causes severe sensitivity to ivermectin, loperamide, vinblastine, and other P-glycoprotein substrates. Always test before prescribing.", "source": "Washington State University VCPL"},
    {"species": "Cat", "category": "Pharmacology", "pearl": "Permethrin spot-on preparations (common in dog flea products) cause fatal pyrethroid toxicosis in cats — profound muscle tremors, hyperthermia, seizures. Never apply dog flea products to cats.", "source": "EMEA/MHRA veterinary pharmacovigilance"},
    {"species": "Dog", "category": "Pharmacology", "pearl": "Metronidazole doses >60 mg/kg/day or prolonged therapy can cause acute vestibular syndrome in dogs (head tilt, nystagmus, ataxia). Usually reversible within 1–2 weeks of cessation.", "source": "Plumb's Veterinary Drug Handbook"},
    {"species": "Horse", "category": "Pharmacology", "pearl": "Oral amoxicillin/ampicillin in horses has very poor bioavailability and disrupts hindgut flora, causing fatal Clostridium-associated colitis. Use IV/IM routes or choose enrofloxacin/trimethoprim-sulfa orally.", "source": "Equine Clinical Pharmacology, Bertone"},
    {"species": "Rabbit", "category": "Pharmacology", "pearl": "Penicillins and most oral antibiotics (amoxicillin, clindamycin, lincomycin) cause fatal antibiotic-associated enterotoxaemia in rabbits and guinea pigs by disrupting cecal flora. Safe options: enrofloxacin, trimethoprim-sulfa, chloramphenicol.", "source": "Exotic Animal Formulary, Carpenter"},
    {"species": "Cat", "category": "Pharmacology", "pearl": "Enrofloxacin at doses >5 mg/kg/day in cats causes irreversible retinal degeneration and blindness. Use marbofloxacin or pradofloxacin as safer feline fluoroquinolone alternatives.", "source": "AAVPT Veterinary Pharmacology"},
    {"species": "Bird", "category": "Pharmacology", "pearl": "Avian drug metabolism is extremely fast. Most drugs require q12–24h dosing in birds (not q24h as in mammals). Doxycycline is the treatment of choice for psittacosis — use oral syrup formulation, not pelleted food.", "source": "Exotic Animal Formulary, Carpenter"},
    {"species": "Dog", "category": "Pharmacology", "pearl": "Grapes and raisins can cause acute renal failure in dogs — mechanism unknown, toxic dose unpredictable, some dogs develop ARF from very small amounts. No safe threshold established.", "source": "ASPCA Animal Poison Control"},
    {"species": "Dog", "category": "Pharmacology", "pearl": "Chocolate toxicity (theobromine/caffeine): dark chocolate > milk chocolate > white chocolate. Toxic dose for theobromine: >20 mg/kg causes GI signs; >40 mg/kg cardiac arrhythmia; >60 mg/kg seizures.", "source": "Plumb's Veterinary Drug Handbook"},
    {"species": "Cat", "category": "Pharmacology", "pearl": "Benzocaine and lidocaine in topical sprays can cause methaemoglobinaemia in cats. Avoid topical anaesthetic sprays; prefer injectable lidocaine with careful dosing.", "source": "Small Animal Clinical Pharmacology"},
    {"species": "Horse", "category": "Pharmacology", "pearl": "Xylazine in cattle requires 1/10th the dose used in horses due to 10× higher sensitivity. Accidental overdose with equine doses causes severe respiratory depression and cardiovascular collapse.", "source": "Large Animal Internal Medicine, Smith"},
    {"species": "Dog", "category": "Pharmacology", "pearl": "Onions, garlic, leeks and chives (Allium spp.) cause dose-dependent Heinz body haemolytic anaemia in dogs and cats. Cats are 5× more sensitive. Clinical signs appear 1–5 days after ingestion.", "source": "ASPCA Animal Poison Control"},

    # Toxicology
    {"species": "Cat", "category": "Toxicology", "pearl": "Essential oil diffusers (tea tree, eucalyptus, pennyroyal) can cause serious hepatotoxicity, CNS depression and respiratory distress in cats, even from passive exposure. Keep cats out of rooms with active diffusers.", "source": "ASPCA Animal Poison Control"},
    {"species": "Bird", "category": "Toxicology", "pearl": "PTFE (Teflon) non-stick coating releases fumes at high heat (>260°C) that are rapidly fatal to birds — pulmonary haemorrhage within minutes. All non-stick cookware must be banned from households with birds.", "source": "Avian Medicine: Principles and Application, Ritchie"},
    {"species": "Dog", "category": "Toxicology", "pearl": "Rat/mouse poisons (brodifacoum, bromadiolone) cause delayed coagulopathy 3–5 days post-ingestion. Always treat with vitamin K1 (phytomenadione) for minimum 4–6 weeks for second-generation anticoagulants.", "source": "Small Animal Toxicology, Peterson"},
    {"species": "Dog", "category": "Toxicology", "pearl": "Macadamia nuts cause reversible neurological syndrome in dogs: hyperthermia, tremors, weakness, ataxia within 12h. Mechanism unknown. Dose: >2 g/kg. Usually self-limiting within 48h.", "source": "ASPCA Animal Poison Control"},
    {"species": "Cat", "category": "Toxicology", "pearl": "Lilies (Lilium and Hemerocallis spp.) are uniquely nephrotoxic to cats — even small amounts (pollen, water from vase) cause acute renal failure. No antidote; survival depends on early IV fluid diuresis.", "source": "ASPCA Animal Poison Control"},
    {"species": "Dog", "category": "Toxicology", "pearl": "Calcium channel blocker (amlodipine, diltiazem, verapamil) toxicity: bradycardia, hypotension, AV block. Treatment: high-dose insulin-dextrose, calcium gluconate, lipid emulsion therapy for severe cases.", "source": "Small Animal Toxicology, Peterson"},

    # Clinical
    {"species": "Dog", "category": "Clinical", "pearl": "Canine brachycephalic syndrome: always pre-oxygenate before anaesthesia, have tracheotomy kit available, use CRI propofol (not mask induction). Extubate as late as possible — these dogs have very narrow airways.", "source": "BSAVA Manual of Canine and Feline Anaesthesia"},
    {"species": "Cat", "category": "Clinical", "pearl": "Feline urethral obstruction: always correct electrolyte imbalances (especially hyperkalaemia) before anaesthesia. ECG should be performed — peaked T waves indicate dangerous hyperkalaemia (>6.5 mEq/L).", "source": "Kirk's Current Veterinary Therapy"},
    {"species": "Dog", "category": "Clinical", "pearl": "GDV (Gastric Dilatation-Volvulus) is a surgical emergency — always decompress the stomach by orogastric tube or trocar before anaesthesia. Large/giant breeds at highest risk, especially after eating then exercising.", "source": "BSAVA Manual of Canine Surgery"},
    {"species": "Horse", "category": "Clinical", "pearl": "Colic in horses: 80% of cases are medical (spasmodic, impaction). Red flags for surgery: failure to respond to analgesics within 30 min, heart rate >60 bpm, absent gut sounds, positive nasogastric reflux >2L.", "source": "Equine Internal Medicine, Reed"},
    {"species": "Cat", "category": "Clinical", "pearl": "Feline asthma vs. heart disease: both cause respiratory distress, but treatment differs completely. Furosemide (cardiac) vs. bronchodilator (asthma). Lateral thoracic radiograph + cardiac echo essential — never stress cat for DV view.", "source": "BSAVA Feline Medicine"},
    {"species": "Dog", "category": "Clinical", "pearl": "Addison's disease (hypoadrenocorticism) — the great imitator. Classic presentation: waxing/waning weakness, vomiting, bradycardia, hyponatraemia + hyperkalaemia (Na:K ratio <27). ACTH stimulation test is diagnostic.", "source": "Ettinger's Textbook of Veterinary Internal Medicine"},
    {"species": "Dog", "category": "Clinical", "pearl": "Diabetic ketoacidosis in dogs: use regular insulin (not long-acting) CRI, initially avoid glucose until BG <250 mg/dL, correct hypophosphataemia (haemolytic anaemia risk), add 0.9% NaCl not Lactated Ringer (K+ additive effects).", "source": "Small Animal Internal Medicine, Nelson"},
    {"species": "Cat", "category": "Clinical", "pearl": "Hyperthyroidism in cats (most common endocrine disease): palpate thyroid for nodule, check BP (hypertension common), evaluate kidneys before treatment — hyperthyroidism masks underlying CKD that worsens post-treatment.", "source": "Feline Internal Medicine, August"},
    {"species": "Horse", "category": "Clinical", "pearl": "PPID (Pituitary Pars Intermedia Dysfunction / Equine Cushing's): hypertrichosis (failure to shed coat) is pathognomonic. Diagnose with overnight dexamethasone suppression test or ACTH measurement. Treat with pergolide.", "source": "Equine Internal Medicine, Reed"},
    {"species": "Dog", "category": "Clinical", "pearl": "Immune-mediated haemolytic anaemia (IMHA): regenerative anaemia + spherocytes + positive Coombs' test. Autoagglutination on saline suspension confirms diagnosis. First-line: prednisolone 1–2 mg/kg/day + thromboprophylaxis (heparin, clopidogrel).", "source": "BSAVA Manual of Canine and Feline Haematology"},
    {"species": "Rabbit", "category": "Clinical", "pearl": "GI stasis in rabbits is a medical emergency — not just 'not eating'. Rabbits cannot vomit; GI hypomotility leads to cecal dysbiosis, hepatic lipidosis, and death within 24–48h. Treatment: fluids, analgesia, gut motility agents, syringe feeding.", "source": "BSAVA Manual of Rabbit Medicine"},
    {"species": "Bird", "category": "Clinical", "pearl": "Psittacine beak and feather disease (PBFD virus) vs nutritional feather dystrophy: always viral test (PCR). Sick birds that are fluffed up and sitting on cage floor have exhausted their reserve — aggressive supportive care needed immediately.", "source": "Avian Medicine: Principles and Application, Ritchie"},
]


@router.get("/clinical-pearls")
async def get_clinical_pearls(
    species: str | None = None,
    user: User = Depends(get_current_user),
):
    """Veterinary clinical pearls — key pharmacology, toxicology and clinical facts."""
    pearls = _CLINICAL_PEARLS
    if species and species != "all":
        pearls = [p for p in pearls if p["species"].lower().startswith(species.lower())]
    return {"pearls": pearls, "total": len(pearls)}


@router.put("/user/veterinary-settings")
async def update_vet_settings(
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Enable or disable veterinary mode for the current user."""
    prefs = user.preferences or {}
    prefs["vet_mode"] = enabled
    user.preferences = prefs
    await db.commit()
    return {"vet_mode": enabled, "detail": f"Veterinary mode {'enabled' if enabled else 'disabled'}"}
