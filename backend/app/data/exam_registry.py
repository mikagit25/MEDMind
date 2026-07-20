"""Gulf & global exam registry seed data — G1.

Parameters sourced from official regulatory body synopses.
All entries start as status='draft' until blueprint_verified_at is confirmed
against the current official document. Set status='active' only after verification.

Blueprint categories map to MCQQuestion.nclex_client_needs where overlap exists.
"""

GULF_BLUEPRINT_CATEGORIES = [
    "fundamentals_nursing",
    "medical_surgical",
    "pharmacology",
    "maternal_newborn",
    "pediatrics",
    "mental_health",
    "community_public_health",
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
        "regulatory_body": "Saudi Commission for Health Specialties (SCHS)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://www.scfhs.org.sa/en/MESPS/TrainingProgs/Pages/Exam.aspx",
        "blueprint_verified_at": None,   # set after official confirmation
        "status": "draft",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
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
        "blueprint_verified_at": None,
        "status": "draft",
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
        "blueprint_verified_at": None,
        "status": "draft",
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
        "blueprint_source": "https://www.omsb.org/licensing",
        "blueprint_verified_at": None,
        "status": "draft",
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
        "blueprint_verified_at": None,
        "status": "draft",
        "locale": "en",
        "family": "gulf",
        "options_per_question": 4,
        "categories": GULF_BLUEPRINT_CATEGORIES,
        "disclaimer": NONAFFILIATION_DISCLAIMER,
    },
    {
        "slug": "moh-uae",
        "name": "MOH UAE Nursing Licensing Exam",
        "country": "UAE — Northern Emirates",
        "regulatory_body": "Ministry of Health and Prevention (MOHAP)",
        "question_count": 100,
        "duration_min": 180,
        "pass_threshold": 65,
        "passing_score_label": "65%",
        "blueprint_source": "https://mohap.gov.ae/en/services/licensing-of-health-professionals",
        "blueprint_verified_at": None,
        "status": "draft",
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
        "blueprint_verified_at": None,
        "status": "draft",
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
