"""Gulf & global exam registry seed data — G1.

Parameters sourced from official regulatory body public synopses (verified 2026-07-20).
Blueprint categories map to MCQQuestion.nclex_client_needs where overlap exists.

SNLE blueprint corrected 2026-07-30 against SCFHS Applicant Guide 2024:
  Adult Nursing 40% | Maternal-Child Nursing 30% | Nursing Fundamentals 20%
  | Nursing Management & Leadership 10%.  Scale 200–800, passing score 500.
"""

# Date all 7 Gulf exam parameters were cross-checked against official regulatory sources
BLUEPRINT_VERIFIED_DATE = "2026-07-20"
SNLE_BLUEPRINT_VERIFIED_DATE = "2026-07-30"   # re-verified from SCFHS Applicant Guide 2024

# Official SNLE categories (SCFHS Applicant Guide 2024)
SNLE_BLUEPRINT_CATEGORIES = [
    "adult_nursing",                 # 40% — medical-surgical, critical care
    "maternal_child_nursing",        # 30% — OB, newborn, pediatrics
    "nursing_fundamentals",          # 20% — fundamentals, pharmacology, basic skills
    "nursing_management_leadership", # 10% — leadership, management, ethics
]

GULF_BLUEPRINT_CATEGORIES = [
    "fundamentals_nursing",
    "medical_surgical",
    "critical_care",
    "pharmacology",
    "maternal_newborn",
    "pediatrics",
    "mental_health",
    "community_public_health",  # includes gerontology (OMSB: 15%)
    "leadership_management",
]

NONAFFILIATION_DISCLAIMER = (
    "MedMind AI is not affiliated with, endorsed by, or connected to this "
    "regulatory body or its examination program. All exam parameters are sourced "
    "from publicly available official synopses. Verify current requirements at "
    "the official source before registering."
)

GULF_EXAMS: list[dict] = [
    {
        "slug": "snle",
        "name": "SNLE — Saudi Nursing Licensing Exam",
        "country": "Saudi Arabia",
        "regulatory_body": "Saudi Commission for Health Specialties (SCFHS)",
        # Source: SCFHS Applicant Guide 2024 — 2 parts × 100 MCQ each, 120 min each + 30 min break
        # Scale 200–800; passing score 500 (500/800 = 62.5%); stored as 63 (ceiling)
        "question_count": 200,
        "duration_min": 270,  # 2 × 120 min + 30 min break
        "pass_threshold": 63,  # 500/800 scale = 62.5%, ceiling → 63
        "passing_score_label": "500/800",
        "blueprint_source": "https://scfhs.org.sa/sites/default/files/2024-10/SNLE%20Applicant%20Guide%202024.pdf",
        "blueprint_verified_at": SNLE_BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        # Official SCFHS 2024 blueprint categories with weights:
        # Adult Nursing 40% | Maternal-Child 30% | Fundamentals 20% | Management 10%
        "categories": SNLE_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "dha",
        "name": "DHA Nursing Licensing Exam",
        "country": "UAE — Dubai",
        "regulatory_body": "Dubai Health Authority (DHA)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://www.dha.gov.ae/en/HealthProfessionals/LicensingandRegistration",
        "blueprint_verified_at": BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "qchp",
        "name": "QCHP Nursing Licensing Exam",
        "country": "Qatar",
        "regulatory_body": "Qatar Council for Healthcare Practitioners (QCHP)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://www.qchp.org.qa/en/Licensing/Pages/LicensingRequirements.aspx",
        "blueprint_verified_at": BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "omsb",
        "name": "OMSB Nursing Licensing Exam",
        "country": "Oman",
        "regulatory_body": "Oman Medical Specialty Board (OMSB)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://omsb.gov.om/ContentFiles/OEN%20BookletYYYY11DD1311SS.pdf",
        "blueprint_verified_at": BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "nhra",
        "name": "NHRA Nursing Licensing Exam",
        "country": "Bahrain",
        "regulatory_body": "National Health Regulatory Authority (NHRA)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://www.nhra.bh/Licensing",
        "blueprint_verified_at": BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "mohuae",
        "name": "MOH UAE Nursing Licensing Exam",
        "country": "UAE — Northern Emirates",
        "regulatory_body": "Ministry of Health and Prevention (MOHAP)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://mohap.gov.ae/en/services/licensing-of-health-professionals",
        "blueprint_verified_at": BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "haad",
        "name": "DOH/HAAD Nursing Licensing Exam",
        "country": "UAE — Abu Dhabi",
        "regulatory_body": "Department of Health Abu Dhabi (DOH)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://www.doh.gov.ae/en/regulatedhealthprofessions/licensingrequirements",
        "blueprint_verified_at": BLUEPRINT_VERIFIED_DATE,
        "status": "active",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
]

# Complete registry — add non-Gulf entries here as phases G4–G6 land
ALL_EXAMS: list[dict] = GULF_EXAMS

# Which NCLEX client-needs categories map to Gulf blueprint categories
# Used by the question mapper script (G1.2)
NCLEX_TO_GULF_CATEGORY_MAP: dict[str, str] = {
    "safe_effective_care":       "fundamentals_nursing",
    "safe_effective_care_environment": "fundamentals_nursing",
    "health_promotion":          "community_public_health",
    "psychosocial":              "mental_health",
    "basic_care":                "fundamentals_nursing",
    "pharmacological":           "pharmacology",
    "reduction_risk":            "medical_surgical",
    "physiological_adaptation":  "medical_surgical",
    "safety":                    "fundamentals_nursing",
    "management_of_care":        "leadership_management",
}
