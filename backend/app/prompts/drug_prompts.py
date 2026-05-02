"""Prompts for drug-related AI queries."""


def generate_drug_profile(drug_name: str, specialty: str) -> str:
    return (
        f"Generate a complete drug profile for: **{drug_name}**\n"
        f"Context specialty: {specialty}\n\n"
        "Include:\n"
        "- Class and mechanism of action\n"
        "- Indications (with evidence grade)\n"
        "- Dosing (adult, typical ranges)\n"
        "- Contraindications and cautions\n"
        "- Key side effects (by frequency)\n"
        "- Important drug interactions\n"
        "- Monitoring parameters\n"
        "- Clinical pearls for prescribers\n\n"
        "End with disclaimer: 'Always verify with current prescribing information.'"
    )


def generate_drug_interactions(drug_list: list[str]) -> str:
    drugs_str = ", ".join(drug_list)
    return (
        f"Analyse potential drug interactions between: {drugs_str}\n\n"
        "For each significant interaction:\n"
        "1. Severity (mild/moderate/severe/contraindicated)\n"
        "2. Mechanism\n"
        "3. Clinical effect\n"
        "4. Management recommendation\n\n"
        "If no significant interactions, state 'No major interactions identified.'\n"
        "Add disclaimer: 'This is for educational purposes. Consult clinical pharmacist for patient-specific advice.'"
    )


def generate_drug_learning_materials(drug_name: str, exam_type: str = "general") -> str:
    return (
        f"Create high-yield learning materials for: **{drug_name}**\n"
        f"Exam focus: {exam_type}\n\n"
        "Format:\n"
        "1. **Mnemonic** — memorable way to recall key facts\n"
        "2. **Top 5 exam points** — most commonly tested facts\n"
        "3. **Common exam traps** — what gets students wrong\n"
        "4. **One-liner** — board-style summary sentence\n"
    )
