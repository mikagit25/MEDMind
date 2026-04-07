"""Prompts for veterinary mode AI queries."""


def generate_vet_module_structure(specialty: str, topic: str, species: str, level: str) -> str:
    return (
        f"Create a veterinary education module:\n"
        f"- Specialty: {specialty}\n"
        f"- Topic: {topic}\n"
        f"- Target species: {species}\n"
        f"- Level: {level}\n\n"
        "Emphasise species-specific physiology, pharmacokinetics, and dosing differences. "
        "Highlight any toxicities that are unique to this species. "
        "Output in the same JSON format as human modules."
    )


def adapt_human_content_to_vet(human_content: str, species: str) -> str:
    return (
        f"Adapt the following human medicine content for veterinary use in {species}:\n\n"
        f"{human_content}\n\n"
        "Modifications needed:\n"
        f"1. Adjust drug dosing for {species} pharmacokinetics\n"
        f"2. Note any drugs that are TOXIC or CONTRAINDICATED in {species}\n"
        f"3. Highlight species-specific disease presentations\n"
        f"4. Replace human-specific references (e.g., 'patient complains of...') with appropriate veterinary language\n\n"
        "CRITICAL: Flag any drugs like paracetamol (cats), xylitol (dogs), or permethrin (cats) "
        "that are commonly used in humans but dangerous for this species."
    )


def generate_species_drug_safety(drug_name: str, species_list: list[str]) -> str:
    species_str = ", ".join(species_list)
    return (
        f"Evaluate the safety of **{drug_name}** for the following species: {species_str}\n\n"
        "For each species:\n"
        "- Safe dose range (or CONTRAINDICATED)\n"
        "- Specific toxicity concerns\n"
        "- Alternative drug if contraindicated\n"
        "- Evidence source (e.g., Plumb's, WSAVA guidelines)\n\n"
        "Flag CONTRAINDICATIONS in CAPITALS."
    )
