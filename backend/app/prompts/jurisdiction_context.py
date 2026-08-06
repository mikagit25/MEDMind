"""L3.1 — Jurisdiction context block injected into Gulf question generation prompts.

Only verified rules (status='verified') enter the prompt.  Rules with
status='needs_human' or 'unverified' are silently omitted.  Domains with
no verified rule are tracked and returned as deficit so the generator can
skip those domains rather than hallucinate local norms.

Usage (inside generate_gulf_questions.py):
    profile_ctx = await build_jurisdiction_context(db, exam_slug="snle")
    prompt = _build_prompt(exam_slug, topic, n, jurisdiction_ctx=profile_ctx)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

EXAM_TO_PROFILE: dict[str, str] = {
    "snle": "sa",
    "dha": "ae_dubai",
    "haad": "ae_abudhabi",
    "doh": "ae_abudhabi",
    "qchp": "qa",
    "omsb": "om",
    "nhra": "bh",
    "moh_kw": "kw",
}

DOMAIN_LABELS: dict[str, str] = {
    "scope_of_practice": "Scope of Practice",
    "medication_administration": "Medication Administration",
    "consent": "Consent",
    "end_of_life": "End-of-Life Care",
    "documentation_reporting": "Documentation & Mandatory Reporting",
    "infection_control": "Infection Control",
    "patient_rights": "Patient Rights",
    "cultural_religious_care": "Cultural & Religious Care",
    "region_salient_clinical": "Regionally Significant Clinical Topics",
    "emergency_activation": "Emergency Activation",
}

ALL_DOMAINS = list(DOMAIN_LABELS.keys())


class JurisdictionContext:
    """Pre-fetched, serialisable jurisdiction context for one exam."""

    def __init__(
        self,
        profile_slug: str,
        country: str,
        regulator: str,
        emergency_numbers: dict,
        locale_primary: str,
        verified_rules: dict[str, list[str]],  # domain → [statement, …]
        deficit_domains: list[str],             # domains with no verified rule
    ) -> None:
        self.profile_slug = profile_slug
        self.country = country
        self.regulator = regulator
        self.emergency_numbers = emergency_numbers
        self.locale_primary = locale_primary
        self.verified_rules = verified_rules
        self.deficit_domains = deficit_domains

    def to_prompt_block(self) -> str:
        """Build the jurisdiction context string to inject into a generation prompt."""
        lines: list[str] = [
            f"=== JURISDICTION CONTEXT: {self.country} ({self.regulator}) ===",
            "",
            "MANDATORY CONSTRAINTS for this jurisdiction (non-negotiable):",
            f"• All units: SI only (mmol/L not mg/dL, °C not °F, kg not lb)",
            f"• Drug names: generic only (no brand names)",
            f"• Emergency numbers: {self._emergency_str()}",
            f"• No references to US law, bodies, or standards (HIPAA, OSHA, Joint Commission, 911, CDC, FDA, DEA)",
            f"• Patient names and contexts must be regionally appropriate",
            "",
        ]

        if self.verified_rules:
            lines.append("VERIFIED LOCAL NORMS (use these; do NOT invent other local norms):")
            for domain, statements in self.verified_rules.items():
                label = DOMAIN_LABELS.get(domain, domain)
                lines.append(f"\n[{label}]")
                for s in statements:
                    lines.append(f"  • {s}")
            lines.append("")

        if self.deficit_domains:
            deficit_labels = [DOMAIN_LABELS.get(d, d) for d in self.deficit_domains]
            lines.append(
                "DOMAINS WITHOUT VERIFIED NORMS (do NOT generate questions on these topics for this exam):"
            )
            for label in deficit_labels:
                lines.append(f"  • {label}")
            lines.append("")

        lines.append("=== END JURISDICTION CONTEXT ===")
        return "\n".join(lines)

    def _emergency_str(self) -> str:
        if not self.emergency_numbers:
            return "see local facility policy"
        parts = [f"{k.capitalize()}: {v}" for k, v in self.emergency_numbers.items()]
        return ", ".join(parts)

    def domain_allowed(self, domain: str) -> bool:
        """True if the domain has at least one verified rule (safe to generate)."""
        return domain in self.verified_rules

    def has_any_verified_rules(self) -> bool:
        return bool(self.verified_rules)


async def build_jurisdiction_context(
    db: "AsyncSession", exam_slug: str
) -> JurisdictionContext | None:
    """Fetch profile + verified rules for an exam slug.  Returns None if no profile found."""
    from sqlalchemy import select
    from app.models.models import JurisdictionProfile, JurisdictionRule

    profile_slug = EXAM_TO_PROFILE.get(exam_slug)
    if not profile_slug:
        return None

    profile = (await db.execute(
        select(JurisdictionProfile).where(JurisdictionProfile.slug == profile_slug)
    )).scalar_one_or_none()
    if not profile:
        return None

    rules = (await db.execute(
        select(JurisdictionRule).where(
            JurisdictionRule.profile_slug == profile_slug,
            JurisdictionRule.status == "verified",
        )
    )).scalars().all()

    verified_by_domain: dict[str, list[str]] = {}
    for rule in rules:
        verified_by_domain.setdefault(rule.domain, []).append(rule.statement)

    deficit = [d for d in ALL_DOMAINS if d not in verified_by_domain]

    return JurisdictionContext(
        profile_slug=profile_slug,
        country=profile.country,
        regulator=profile.regulator,
        emergency_numbers=profile.emergency_numbers or {},
        locale_primary=profile.locale_primary,
        verified_rules=verified_by_domain,
        deficit_domains=deficit,
    )
