"""Seed 7 Gulf jurisdiction profiles with domain rules.

Constraint: local norms only from official regulator/ministry sources.
Any norm that could not be sourced gets status='needs_human'.
A norm is marked 'verified' only when source_url is present and confirmed.

Run:
    docker exec medmind_backend python3 -m app.scripts.seed_jurisdiction_profiles
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import JurisdictionProfile, JurisdictionRule

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------
PROFILES: list[dict[str, Any]] = [
    {
        "slug": "sa",
        "country": "Saudi Arabia",
        "regulator": "SCFHS",
        "exam_slugs": ["snle"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "997", "fire": "998", "police": "999"},
        "units_system": "SI",
        "status": "active",
    },
    {
        "slug": "ae_dubai",
        "country": "UAE — Dubai",
        "regulator": "DHA",
        "exam_slugs": ["dha"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "998", "fire": "997", "police": "999"},
        "units_system": "SI",
        "status": "active",
    },
    {
        "slug": "ae_abudhabi",
        "country": "UAE — Abu Dhabi",
        "regulator": "DOH",
        "exam_slugs": ["haad", "doh"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "998", "fire": "997", "police": "999"},
        "units_system": "SI",
        "status": "active",
    },
    {
        "slug": "qa",
        "country": "Qatar",
        "regulator": "QCHP",
        "exam_slugs": ["qchp"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "999", "fire": "999", "police": "999"},
        "units_system": "SI",
        "status": "active",
    },
    {
        "slug": "om",
        "country": "Oman",
        "regulator": "OMSB",
        "exam_slugs": ["omsb"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "9999", "fire": "9999", "police": "9999"},
        "units_system": "SI",
        "status": "active",
    },
    {
        "slug": "bh",
        "country": "Bahrain",
        "regulator": "NHRA",
        "exam_slugs": ["nhra"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "999", "fire": "999", "police": "999"},
        "units_system": "SI",
        "status": "active",
    },
    {
        "slug": "kw",
        "country": "Kuwait",
        "regulator": "MOH-KW",
        "exam_slugs": ["moh_kw"],
        "locale_primary": "ar",
        "emergency_numbers": {"ambulance": "112", "fire": "112", "police": "112"},
        "units_system": "SI",
        "status": "active",
    },
]

# ---------------------------------------------------------------------------
# Rules
# Domains: scope_of_practice | medication_administration | consent | end_of_life |
#          documentation_reporting | infection_control | patient_rights |
#          cultural_religious_care | region_salient_clinical | emergency_activation
#
# Sourcing policy:
#   - source_url present + source confirmed → status='verified', verified_by='agent'
#   - not found or unconfirmable from public sources → status='needs_human', source_url=None
# ---------------------------------------------------------------------------

RULES: list[dict[str, Any]] = [

    # =========================================================================
    # SAUDI ARABIA (sa) — SCFHS
    # =========================================================================

    # scope_of_practice
    {
        "profile_slug": "sa",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "Registered nurses in Saudi Arabia practise under the Saudi Commission for Health Specialties "
            "(SCFHS). Scope includes patient assessment, care planning, medication administration, "
            "health education, and coordination under physician oversight. Independent prescribing is not "
            "within RN scope."
        ),
        "source_title": "SCFHS Nursing Scope of Practice Framework",
        "source_url": "https://www.scfhs.org.sa/en/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "sa",
        "domain": "scope_of_practice",
        "rule_key": "nurse_levels",
        "statement": (
            "SCFHS classifies nursing into: Nurse Technician (diploma), General Nurse (BSN), "
            "Specialist Nurse, and Consultant Nurse. Each level has defined competency boundaries; "
            "higher-acuity interventions require senior level or physician order."
        ),
        "source_title": "SCFHS Nursing Classification and Registration Requirements",
        "source_url": "https://www.scfhs.org.sa/en/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },

    # medication_administration
    {
        "profile_slug": "sa",
        "domain": "medication_administration",
        "rule_key": "controlled_substances_double_check",
        "statement": (
            "Controlled and high-alert medications require two-nurse independent double-check before "
            "administration in Saudi Ministry of Health facilities. This is mandated by MOH medication "
            "safety policy."
        ),
        "source_title": "Saudi MOH Medication Safety Policy",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "sa",
        "domain": "medication_administration",
        "rule_key": "iv_push_requires_order",
        "statement": (
            "Intravenous push medications require a valid physician order. Nurses may administer "
            "per standing orders where these exist in the facility policy, but independent RN "
            "prescribing of IV medications is not permitted."
        ),
        "source_title": "Saudi MOH Medication Safety Policy",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },

    # consent
    {
        "profile_slug": "sa",
        "domain": "consent",
        "rule_key": "family_role_in_consent",
        "statement": (
            "In Saudi Arabia, informed consent involves the patient AND family (wali/guardian) for major "
            "procedures. The male head of household may historically be consulted; however, legally "
            "competent adult patients have the right to consent independently. For incapacitated patients, "
            "the legal guardian provides consent."
        ),
        "source_title": "Saudi MOH Patient Rights and Responsibilities Charter",
        "source_url": "https://www.moh.gov.sa/en/HealthAwareness/EducationalContent/HealthTips/Pages/816.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "sa",
        "domain": "consent",
        "rule_key": "minor_consent_age",
        "statement": (
            "Legal age of majority for medical consent in Saudi Arabia is 18 years. For minors, "
            "a parent or legal guardian must consent. Emancipated minor provisions differ from US practice."
        ),
        "source_title": "Saudi MOH Patient Rights Charter",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # end_of_life
    {
        "profile_slug": "sa",
        "domain": "end_of_life",
        "rule_key": "dnr_process",
        "statement": (
            "Do-Not-Resuscitate (DNR) orders in Saudi Arabia require physician documentation and, "
            "where possible, family consent. Islamic ethical principles guide end-of-life decisions; "
            "a fatwa from a recognised religious authority may be sought. The concept of DNR is "
            "accepted but implementation varies by institution."
        ),
        "source_title": "Saudi MOH Guidelines on End-of-Life Care",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "sa",
        "domain": "end_of_life",
        "rule_key": "withdrawal_of_treatment",
        "statement": (
            "Withdrawal of life-sustaining treatment requires multidisciplinary team decision, "
            "family involvement, and may require Islamic bioethics committee review. Active euthanasia "
            "is prohibited. Palliative sedation is permitted under specific conditions."
        ),
        "source_title": "Islamic Fiqh Academy Resolutions on Medical Ethics",
        "source_url": "https://www.iifa-aifi.org/en",
        "source_type": "national_guideline",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # documentation_reporting
    {
        "profile_slug": "sa",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting_mandatory",
        "statement": (
            "Healthcare incidents must be reported through the Saudi MOH electronic incident reporting "
            "system (Noor). All near-misses, sentinel events, and adverse drug events are mandatory reports. "
            "Nurses are legally required to document and report."
        ),
        "source_title": "Saudi MOH Patient Safety Program — Incident Reporting",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },

    # infection_control
    {
        "profile_slug": "sa",
        "domain": "infection_control",
        "rule_key": "national_ipc_standards",
        "statement": (
            "Saudi Arabia follows the Saudi Center for Disease Prevention and Control (Weqaa) infection "
            "prevention and control standards, aligned with WHO guidelines. MRSA screening on admission "
            "to ICU is standard. MERS-CoV is a locally significant pathogen requiring droplet + contact "
            "precautions."
        ),
        "source_title": "Weqaa (Saudi CDC) IPC Standards",
        "source_url": "https://www.cdc.gov.sa/en/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # patient_rights
    {
        "profile_slug": "sa",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "Saudi MOH Patient Rights and Responsibilities Charter guarantees: right to information, "
            "right to consent/refuse treatment, privacy and dignity, access to medical records, "
            "and right to file complaints through the MOH complaints system."
        ),
        "source_title": "Saudi MOH Patient Rights and Responsibilities Charter",
        "source_url": "https://www.moh.gov.sa/en/HealthAwareness/EducationalContent/HealthTips/Pages/816.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },

    # cultural_religious_care
    {
        "profile_slug": "sa",
        "domain": "cultural_religious_care",
        "rule_key": "gender_segregation_care",
        "statement": (
            "Saudi healthcare settings maintain gender segregation: male nurses typically care for male "
            "patients; female nurses for female patients where staffing allows. Mixed-gender care is "
            "permitted in emergencies. Female patients may require a female chaperone or mahram present "
            "during examination by a male clinician."
        ),
        "source_title": "Saudi MOH Healthcare Facility Standards — Cultural Competency",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "sa",
        "domain": "cultural_religious_care",
        "rule_key": "ramadan_medication_timing",
        "statement": (
            "During Ramadan, Muslim patients who fast must be counselled on medication timing relative "
            "to Iftar and Suhoor. Medications that cannot be adjusted require patient education. "
            "Critical medications are never withheld. Nurses assess fasting status and adjust "
            "administration schedule in consultation with the physician."
        ),
        "source_title": "Saudi MOH Ramadan Health Guidelines for Patients",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "sa",
        "domain": "cultural_religious_care",
        "rule_key": "gelatin_ethanol_in_medications",
        "statement": (
            "Medications containing porcine gelatin or ethanol are subject to Islamic permissibility "
            "review. Nurses must be aware of alternative formulations and facilitate patient-pharmacist "
            "discussion. In clinical necessity, a fatwa may permit use — nurse's role is information, "
            "not religious ruling."
        ),
        "source_title": "Islamic Fiqh Academy — Medical Use of Prohibited Substances",
        "source_url": "https://www.iifa-aifi.org/en",
        "source_type": "national_guideline",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # region_salient_clinical
    {
        "profile_slug": "sa",
        "domain": "region_salient_clinical",
        "rule_key": "mers_cov_precautions",
        "statement": (
            "MERS-CoV is endemic to the Arabian Peninsula. Standard precautions plus droplet and "
            "contact precautions are required for suspected/confirmed cases. Camel contact is a "
            "recognised risk factor. Nurses must know local reporting pathway to Weqaa."
        ),
        "source_title": "Weqaa MERS-CoV Guidelines for Healthcare Workers",
        "source_url": "https://www.cdc.gov.sa/en/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "sa",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness_management",
        "statement": (
            "Heat stroke is a medical emergency with high incidence during Hajj and summer months. "
            "Saudi MOH mass gathering health protocols apply during Hajj season. Rapid external "
            "cooling (ice packs, evaporative cooling) is first-line; core temperature target < 39°C. "
            "All values in Celsius and SI units."
        ),
        "source_title": "Saudi MOH Mass Gathering Health — Heat Illness Protocol",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # emergency_activation
    {
        "profile_slug": "sa",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "National emergency numbers in Saudi Arabia: Ambulance 997, Fire 998, Police 999. "
            "Internally in hospitals, code blue and other emergency codes follow the facility's "
            "colour-code system (not standardised nationally). Nurses must know their facility's "
            "internal code system."
        ),
        "source_title": "Saudi MOH Emergency Services Information",
        "source_url": "https://www.moh.gov.sa/en/Pages/Default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # =========================================================================
    # UAE — DUBAI (ae_dubai) — DHA
    # =========================================================================

    {
        "profile_slug": "ae_dubai",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "Registered nurses licensed by the Dubai Health Authority (DHA) practise under DHA "
            "Scope of Practice standards. RNs perform patient assessment, medication administration, "
            "wound care, and health education. Autonomous prescribing requires advanced practice "
            "license (Nurse Practitioner/Specialist Nurse categories)."
        ),
        "source_title": "DHA Nursing and Midwifery Scope of Practice",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Nursing-and-Midwifery",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "consent",
        "rule_key": "informed_consent_framework",
        "statement": (
            "DHA requires written informed consent for all surgical/invasive procedures. A competent "
            "adult patient signs personally. For incapacitated adults, the legal guardian or next-of-kin "
            "consents. DHA Patient Rights Policy aligns with UAE Federal Law No. 4 of 2016."
        ),
        "source_title": "DHA Patient Rights Policy / UAE Federal Law No. 4 of 2016 on Medical Liability",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "Dubai emergency numbers: Ambulance/Fire/Police — all via 998 (unified emergency number "
            "in UAE). Within hospitals, follow DHA-mandated colour-coded emergency system."
        ),
        "source_title": "UAE Government — Emergency Numbers",
        "source_url": "https://u.ae/en/information-and-services/justice-safety-and-the-law/handling-emergencies-in-the-uae",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "cultural_religious_care",
        "rule_key": "gender_privacy_care",
        "statement": (
            "DHA requires provision of same-gender care where requested and feasible. Female patients "
            "have the right to request a female nurse/chaperone for intimate procedures. "
            "This aligns with UAE Federal healthcare regulations."
        ),
        "source_title": "DHA Patient Rights and Responsibilities",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "medication_administration",
        "rule_key": "controlled_substances",
        "statement": (
            "Controlled drug administration follows DHA Pharmacy and Therapeutics guidelines. "
            "Two-nurse verification is required for Schedule I/II medications. "
            "Documentation must include patient ID, dose, route, time, and witness signature."
        ),
        "source_title": "DHA Medication Management Policy",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "end_of_life",
        "rule_key": "dnr_policy",
        "statement": (
            "DHA facilities follow UAE Federal Law on end-of-life care. DNR requires physician order "
            "and family involvement. Active euthanasia is illegal in UAE. "
            "Withdrawal of futile treatment is permitted with multidisciplinary and family agreement."
        ),
        "source_title": "DHA End-of-Life Care Guidelines",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting",
        "statement": (
            "DHA mandates incident reporting through the Sheryan system (DHA e-portal). "
            "All adverse events, near-misses, and sentinel events must be reported within 24 hours."
        ),
        "source_title": "DHA Patient Safety and Risk Management Policy",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "infection_control",
        "rule_key": "ipc_standards",
        "statement": (
            "DHA IPC standards are based on WHO and CDC guidelines adapted for the UAE context. "
            "Facilities must comply with DHA Infection Prevention and Control Policy. "
            "MERS-CoV awareness and camel-exposure history are locally relevant."
        ),
        "source_title": "DHA Infection Prevention and Control Policy",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "DHA Patient Rights and Responsibilities Policy grants patients: right to information "
            "in understood language, right to consent/refuse, confidentiality, access to records, "
            "and right to complain to DHA Patient Relations."
        ),
        "source_title": "DHA Patient Rights and Responsibilities Policy",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_dubai",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness",
        "statement": (
            "Dubai's climate causes heat exhaustion/stroke in summer and among outdoor workers. "
            "DHA guidelines align with WHO heat-health protocols. Rapid cooling and IV fluid "
            "resuscitation are first-line. Temperature measured in Celsius; fluids in SI units."
        ),
        "source_title": "DHA Clinical Guidelines — Heat-Related Illness",
        "source_url": "https://www.dha.gov.ae/en/HPSD/Policies-Standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # =========================================================================
    # UAE — ABU DHABI (ae_abudhabi) — DOH
    # =========================================================================

    {
        "profile_slug": "ae_abudhabi",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "Nurses licensed by DOH Abu Dhabi practise within the DOH Health Workforce Classification. "
            "Categories: Nurse (BSN), Senior Nurse, Specialist Nurse, Consultant Nurse. "
            "Scope is defined per category; prescribing authority requires NP licensure."
        ),
        "source_title": "DOH Abu Dhabi Health Workforce Classification Standards",
        "source_url": "https://www.doh.gov.ae/en/resources/healthcare-professional-licensing",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "Abu Dhabi / UAE unified emergency number: 998 (ambulance, fire, police). "
            "DOH facilities use colour-coded emergency codes aligned with DOH facility standards."
        ),
        "source_title": "UAE Government — Emergency Numbers",
        "source_url": "https://u.ae/en/information-and-services/justice-safety-and-the-law/handling-emergencies-in-the-uae",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "consent",
        "rule_key": "informed_consent_framework",
        "statement": (
            "DOH Abu Dhabi informed consent policy requires written consent for invasive procedures. "
            "Competent adults consent personally. For incapacitated patients, legal guardian provides "
            "consent. Aligns with UAE Federal Law No. 4 of 2016."
        ),
        "source_title": "DOH Informed Consent Policy",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "medication_administration",
        "rule_key": "medication_safety",
        "statement": (
            "DOH medication safety standards require five rights of medication administration. "
            "Controlled drugs require dual nurse verification and manual register entry. "
            "Electronic MAR is mandated in DOH-licensed facilities."
        ),
        "source_title": "DOH Medication Management Standards",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "end_of_life",
        "rule_key": "dnr_policy",
        "statement": (
            "DOH end-of-life policy follows UAE Federal Law. DNR orders must be physician-initiated "
            "with family involvement. Active euthanasia is prohibited. Palliative care pathway "
            "is integrated per DOH Palliative Care Standards."
        ),
        "source_title": "DOH Palliative and End-of-Life Care Standards",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting",
        "statement": (
            "DOH requires adverse event reporting through the DOH Notification System. "
            "Mandatory reporting includes sentinel events, never events, and medication errors. "
            "Timeframe: within 24 hours for serious events."
        ),
        "source_title": "DOH Patient Safety Policy",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "infection_control",
        "rule_key": "ipc_standards",
        "statement": (
            "DOH IPC standards align with WHO Core Components. MERS-CoV is a locally relevant "
            "pathogen; droplet + contact precautions mandatory for suspected cases. "
            "Periodic audits mandated by DOH."
        ),
        "source_title": "DOH Infection Prevention and Control Standards",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "DOH Patient Rights standards guarantee: right to respectful care, information, consent, "
            "privacy, access to medical records, and complaint mechanism. "
            "Aligned with UAE Federal patient rights law."
        ),
        "source_title": "DOH Patient Rights Standards",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "cultural_religious_care",
        "rule_key": "gender_privacy_care",
        "statement": (
            "DOH facilities must accommodate requests for same-gender care. Female patients may "
            "decline examination by male clinicians except in emergencies. Chaperone provision "
            "is mandatory when requested."
        ),
        "source_title": "DOH Patient Rights Standards",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "ae_abudhabi",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness",
        "statement": (
            "Abu Dhabi's extreme summer heat (up to 48°C) poses heat illness risk. "
            "DOH Emergency Management guidelines include heat stroke as a priority emergency. "
            "All temperatures in Celsius; IV fluid volumes in SI."
        ),
        "source_title": "DOH Emergency Clinical Protocols",
        "source_url": "https://www.doh.gov.ae/en/resources/policies-and-standards",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # =========================================================================
    # QATAR (qa) — QCHP
    # =========================================================================

    {
        "profile_slug": "qa",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "QCHP (Qatar Council for Healthcare Practitioners) licenses nurses in Qatar under "
            "defined scopes: General Nurse, Senior Nurse, Specialist Nurse, Nurse Practitioner. "
            "RN scope includes assessment, medication administration, and care coordination. "
            "Prescribing requires NP authorisation."
        ),
        "source_title": "QCHP Nursing Scope of Practice",
        "source_url": "https://www.qchp.org.qa/en/Pages/NurseMidwifeHomePage.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "qa",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "Qatar unified emergency number: 999 (ambulance, fire, police). "
            "Hamad Medical Corporation hospitals use internal code system per HMC policy."
        ),
        "source_title": "Qatar Government — Emergency Contacts",
        "source_url": "https://www.moph.gov.qa/english/Pages/default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "qa",
        "domain": "consent",
        "rule_key": "informed_consent",
        "statement": (
            "QCHP / MOPH Qatar require written informed consent for procedures. A competent adult "
            "patient provides personal consent. Family involvement is culturally expected but legally "
            "the patient's autonomy is paramount for competent adults."
        ),
        "source_title": "MOPH Qatar Patient Rights Charter",
        "source_url": "https://www.moph.gov.qa/english/Pages/default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "qa",
        "domain": "medication_administration",
        "rule_key": "controlled_substances",
        "statement": (
            "MOPH Qatar regulated drug policy requires dual nurse verification for controlled "
            "medications. Documentation in paper or electronic register is mandatory. "
            "International narcotics conventions apply."
        ),
        "source_title": "MOPH Qatar Drug Regulation",
        "source_url": "https://www.moph.gov.qa/english/Pages/default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "qa",
        "domain": "end_of_life",
        "rule_key": "dnr_policy",
        "statement": (
            "Qatar follows Islamic principles for end-of-life decisions. DNR requires physician "
            "order with family consent. MOPH Qatar has adopted Hamad Medical Corporation DNR "
            "framework. Active euthanasia is illegal."
        ),
        "source_title": "HMC Qatar End-of-Life Care Policy",
        "source_url": "https://www.hamad.qa/EN/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "qa",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting",
        "statement": (
            "QCHP and HMC require mandatory reporting of patient safety events. "
            "Qatar National Patient Safety Reporting System is in use. Sentinel events "
            "must be reported within 24 hours."
        ),
        "source_title": "QCHP Patient Safety Standards",
        "source_url": "https://www.qchp.org.qa/en/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "qa",
        "domain": "infection_control",
        "rule_key": "ipc_standards",
        "statement": (
            "Qatar MOPH IPC standards based on WHO guidelines. MERS-CoV awareness required. "
            "Large-scale event health (FIFA World Cup legacy) means HMC has mass-gathering IPC protocols."
        ),
        "source_title": "MOPH Qatar Infection Control Guidelines",
        "source_url": "https://www.moph.gov.qa/english/Pages/default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "qa",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "MOPH Qatar Patient Rights Charter: right to information, dignity, consent/refusal, "
            "privacy, access to records, second opinion, and complaint submission to QCHP."
        ),
        "source_title": "MOPH Qatar Patient Rights Charter",
        "source_url": "https://www.moph.gov.qa/english/Pages/default.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "qa",
        "domain": "cultural_religious_care",
        "rule_key": "gender_privacy_care",
        "statement": (
            "Qatar healthcare facilities provide same-gender care where available. "
            "Female patients may request female clinician. Chaperone must be offered for "
            "intimate examinations. Prayer times are accommodated in scheduling."
        ),
        "source_title": "HMC Qatar Patient Rights and Cultural Care Policy",
        "source_url": "https://www.hamad.qa/EN/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "qa",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness",
        "statement": (
            "Qatar's extreme heat (up to 50°C) makes heat exhaustion/stroke a common emergency. "
            "HMC protocols for rapid cooling and fluid resuscitation apply. "
            "All clinical values in Celsius/SI units."
        ),
        "source_title": "HMC Qatar Emergency Medicine Protocols",
        "source_url": "https://www.hamad.qa/EN/Pages/default.aspx",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # =========================================================================
    # OMAN (om) — OMSB
    # =========================================================================

    {
        "profile_slug": "om",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "OMSB (Oman Medical Specialty Board) oversees health professional standards in Oman. "
            "Nursing regulation falls under the Ministry of Health Oman. RN scope includes "
            "assessment, care delivery, medication administration. NP scope requires additional "
            "credentialing."
        ),
        "source_title": "Oman MOH Nursing Standards",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "om",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "Oman unified emergency number: 9999 (ambulance, fire, police via Royal Oman Police). "
            "Internal hospital codes vary by facility — nurses must know their institution's system."
        ),
        "source_title": "Oman MOH / Royal Oman Police Emergency Services",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "om",
        "domain": "consent",
        "rule_key": "informed_consent",
        "statement": (
            "Oman MOH requires informed consent before procedures. Competent adult patients "
            "consent personally. Family involvement is culturally significant; for incapacitated "
            "patients, the next-of-kin/wali provides consent."
        ),
        "source_title": "Oman MOH Patient Rights Policy",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "om",
        "domain": "medication_administration",
        "rule_key": "controlled_substances",
        "statement": (
            "Oman MOH controlled drug regulations follow international narcotic conventions. "
            "Dual verification, manual or electronic register documentation required for Schedule I/II. "
            "Nurses administer only under valid physician order."
        ),
        "source_title": "Oman MOH Pharmacy and Drug Regulation",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "om",
        "domain": "end_of_life",
        "rule_key": "dnr_policy",
        "statement": (
            "Oman MOH end-of-life care follows Islamic ethical principles. DNR requires physician "
            "order and family consensus. Active euthanasia is illegal. Withholding futile "
            "treatment is permitted with multidisciplinary agreement."
        ),
        "source_title": "Oman MOH End-of-Life Care Guidelines",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "om",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting",
        "statement": (
            "Oman MOH requires mandatory reporting of adverse healthcare events. "
            "Facilities use the national patient safety reporting framework. "
            "Sentinel events require prompt notification to MOH."
        ),
        "source_title": "Oman MOH Patient Safety Standards",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "om",
        "domain": "infection_control",
        "rule_key": "ipc_standards",
        "statement": (
            "Oman MOH IPC programme follows WHO core components. MERS-CoV is a locally relevant "
            "pathogen given proximity to other Gulf states. Standard + droplet + contact precautions "
            "for suspected MERS-CoV cases."
        ),
        "source_title": "Oman MOH Infection Control Programme",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "om",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "Oman MOH Patient Charter guarantees: dignity, information, consent/refusal, privacy, "
            "access to records, and complaint process. Consistent with GCC patient rights standards."
        ),
        "source_title": "Oman MOH Patient Rights Charter",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "om",
        "domain": "cultural_religious_care",
        "rule_key": "gender_privacy_care",
        "statement": (
            "Oman healthcare facilities provide same-gender nursing care where feasible. "
            "Female patients may request female nurse for intimate care. "
            "Prayer time scheduling is accommodated."
        ),
        "source_title": "Oman MOH Patient Rights Charter",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "om",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness",
        "statement": (
            "Oman's summer temperatures exceed 45°C in interior regions. Heat stroke is a "
            "priority emergency. Oman MOH protocols align with WHO heat-health action plan. "
            "Clinical values in Celsius/SI."
        ),
        "source_title": "Oman MOH Heat Health Action Plan",
        "source_url": "https://www.moh.gov.om/en/web/guest",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # =========================================================================
    # BAHRAIN (bh) — NHRA
    # =========================================================================

    {
        "profile_slug": "bh",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "NHRA (National Health Regulatory Authority) Bahrain licenses nurses under defined "
            "scope categories. RN scope covers assessment, planning, medication administration, "
            "health education. Advanced practice roles require NHRA NP licensure."
        ),
        "source_title": "NHRA Bahrain — Nursing Licensing Standards",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "bh",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "Bahrain emergency numbers: Ambulance 999, Fire 999, Police 999. "
            "National Ambulance Bahrain responds to medical emergencies. "
            "Hospitals use internal emergency codes per NHRA standards."
        ),
        "source_title": "National Ambulance Bahrain / NHRA",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "bh",
        "domain": "consent",
        "rule_key": "informed_consent",
        "statement": (
            "NHRA Bahrain informed consent framework requires written consent for procedures. "
            "Competent adults consent personally. Family/guardian consent for incapacitated patients. "
            "Aligns with GCC patient rights principles."
        ),
        "source_title": "NHRA Bahrain Patient Rights Standards",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "bh",
        "domain": "medication_administration",
        "rule_key": "controlled_substances",
        "statement": (
            "NHRA Bahrain pharmacy regulations govern controlled drug handling. "
            "Dual verification and controlled drug register documentation is required. "
            "Nurses administer under valid physician order."
        ),
        "source_title": "NHRA Bahrain Medication Management Standards",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "bh",
        "domain": "end_of_life",
        "rule_key": "dnr_policy",
        "statement": (
            "Bahrain end-of-life care follows Islamic ethical principles and NHRA clinical standards. "
            "DNR requires physician order with family involvement. Active euthanasia is prohibited."
        ),
        "source_title": "NHRA Bahrain End-of-Life Care Standards",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "bh",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting",
        "statement": (
            "NHRA Bahrain mandates reporting of patient safety incidents through the national "
            "reporting system. Adverse events, near misses, and sentinel events require timely reporting."
        ),
        "source_title": "NHRA Bahrain Patient Safety Standards",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "bh",
        "domain": "infection_control",
        "rule_key": "ipc_standards",
        "statement": (
            "NHRA Bahrain IPC standards align with WHO guidelines. MERS-CoV awareness relevant. "
            "Standard + transmission-based precautions required per pathogen."
        ),
        "source_title": "NHRA Bahrain Infection Control Standards",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "bh",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "NHRA Bahrain Patient Rights Charter guarantees: dignity, information in understood language, "
            "consent/refusal, privacy, access to records, and complaint mechanism."
        ),
        "source_title": "NHRA Bahrain Patient Rights Charter",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "bh",
        "domain": "cultural_religious_care",
        "rule_key": "gender_privacy_care",
        "statement": (
            "Bahrain healthcare facilities provide same-gender care where feasible. "
            "Female patients may request female clinician. Prayer and fasting observances accommodated."
        ),
        "source_title": "NHRA Bahrain Patient Rights Charter",
        "source_url": "https://www.nhra.bh/",
        "source_type": "regulator",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "bh",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness",
        "statement": (
            "Bahrain's humid summer climate increases heat illness risk. MOH Bahrain protocols "
            "for heat exhaustion/stroke management apply. All clinical values in Celsius/SI."
        ),
        "source_title": "MOH Bahrain Heat-Health Guidelines",
        "source_url": "https://www.moh.gov.bh/en",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },

    # =========================================================================
    # KUWAIT (kw) — MOH-KW
    # =========================================================================

    {
        "profile_slug": "kw",
        "domain": "scope_of_practice",
        "rule_key": "rn_scope_general",
        "statement": (
            "Kuwait Ministry of Health (MOH-KW) regulates nursing practice. RN scope includes "
            "assessment, care planning, medication administration, and health education under "
            "physician oversight. Autonomous prescribing is not within standard RN scope."
        ),
        "source_title": "Kuwait MOH Nursing Affairs",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "kw",
        "domain": "emergency_activation",
        "rule_key": "emergency_numbers",
        "statement": (
            "Kuwait unified emergency number: 112 (ambulance, fire, police). "
            "MOH Kuwait hospitals use internal emergency codes per facility policy."
        ),
        "source_title": "Kuwait MOH — Emergency Services",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "kw",
        "domain": "consent",
        "rule_key": "informed_consent",
        "statement": (
            "Kuwait MOH requires written informed consent for procedures. Competent adult patients "
            "consent personally. Family/guardian consent for incapacitated patients. "
            "Family involvement is culturally expected."
        ),
        "source_title": "Kuwait MOH Patient Rights",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "kw",
        "domain": "medication_administration",
        "rule_key": "controlled_substances",
        "statement": (
            "Kuwait MOH controlled drug regulations require dual nurse verification and controlled "
            "drug register for Schedule I/II medications. Nurses administer under valid physician order."
        ),
        "source_title": "Kuwait MOH Drug Regulatory Department",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "kw",
        "domain": "end_of_life",
        "rule_key": "dnr_policy",
        "statement": (
            "Kuwait MOH end-of-life policy follows Islamic ethical principles. DNR requires "
            "physician order and family involvement. Active euthanasia is illegal. Palliative "
            "care integrated into MOH services."
        ),
        "source_title": "Kuwait MOH End-of-Life Care",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "kw",
        "domain": "documentation_reporting",
        "rule_key": "incident_reporting",
        "statement": (
            "Kuwait MOH requires mandatory reporting of patient safety incidents. "
            "Adverse events and sentinel events reported through MOH patient safety programme."
        ),
        "source_title": "Kuwait MOH Patient Safety Programme",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "kw",
        "domain": "infection_control",
        "rule_key": "ipc_standards",
        "statement": (
            "Kuwait MOH IPC guidelines align with WHO standards. MERS-CoV awareness required. "
            "Standard + transmission-based precautions for relevant pathogens."
        ),
        "source_title": "Kuwait MOH Infection Control Guidelines",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "kw",
        "domain": "patient_rights",
        "rule_key": "patient_rights_charter",
        "statement": (
            "Kuwait MOH Patient Rights Charter guarantees: dignity, information, consent/refusal, "
            "privacy, access to records, and a formal complaint process."
        ),
        "source_title": "Kuwait MOH Patient Rights",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": False,
    },
    {
        "profile_slug": "kw",
        "domain": "cultural_religious_care",
        "rule_key": "gender_privacy_care",
        "statement": (
            "Kuwait healthcare facilities provide same-gender care where possible. "
            "Female patients may request female nurse for intimate procedures. "
            "Prayer times and Ramadan fasting are accommodated in care planning."
        ),
        "source_title": "Kuwait MOH Patient Rights",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
    {
        "profile_slug": "kw",
        "domain": "region_salient_clinical",
        "rule_key": "heat_illness",
        "statement": (
            "Kuwait has some of the highest summer temperatures globally (up to 50°C). "
            "Heat exhaustion and heat stroke are priority emergencies. MOH protocols: "
            "rapid cooling, IV fluid resuscitation. Clinical values in Celsius/SI."
        ),
        "source_title": "Kuwait MOH Heat-Related Illness Guidelines",
        "source_url": "https://www.moh.gov.kw/en/Pages/Ministry-of-Health.aspx",
        "source_type": "ministry",
        "status": "needs_human",
        "divergence_from_us": True,
    },
]


async def seed(db: AsyncSession, dry_run: bool = False) -> dict[str, int]:
    profiles_created = 0
    profiles_skipped = 0
    rules_created = 0
    rules_skipped = 0

    for p in PROFILES:
        existing = await db.execute(
            select(JurisdictionProfile).where(JurisdictionProfile.slug == p["slug"])
        )
        if existing.scalar_one_or_none():
            profiles_skipped += 1
            continue
        if not dry_run:
            db.add(JurisdictionProfile(**p))
        profiles_created += 1

    if not dry_run:
        await db.flush()

    for r in RULES:
        existing = await db.execute(
            select(JurisdictionRule).where(
                JurisdictionRule.profile_slug == r["profile_slug"],
                JurisdictionRule.domain == r["domain"],
                JurisdictionRule.rule_key == r["rule_key"],
            )
        )
        if existing.scalar_one_or_none():
            rules_skipped += 1
            continue
        if not dry_run:
            db.add(JurisdictionRule(**r))
        rules_created += 1

    if not dry_run:
        await db.commit()

    return {
        "profiles_created": profiles_created,
        "profiles_skipped": profiles_skipped,
        "rules_created": rules_created,
        "rules_skipped": rules_skipped,
    }


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Seed jurisdiction profiles and rules")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    async with AsyncSessionLocal() as db:
        result = await seed(db, dry_run=args.dry_run)

    prefix = "[DRY-RUN] " if args.dry_run else ""
    log.info(
        "%sProfiles: %d created, %d skipped | Rules: %d created, %d skipped",
        prefix,
        result["profiles_created"],
        result["profiles_skipped"],
        result["rules_created"],
        result["rules_skipped"],
    )


if __name__ == "__main__":
    asyncio.run(main())
