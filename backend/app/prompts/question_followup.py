"""V7 Phase 4 — Question follow-up AI prompt.

Used when a student asks "Explain differently" after seeing an answer explanation.
Context includes the question, their selected answer, and the correct answer.
Chip types direct the style of follow-up.
"""

CHIP_INSTRUCTIONS = {
    "explain_differently": (
        "Re-explain the correct answer using a completely different approach — "
        "try an analogy, a clinical story, or a visual mental model. "
        "Do not repeat the base explanation word-for-word."
    ),
    "why_not_distractor": (
        "The student wants to understand why their selected option was wrong. "
        "Focus specifically on the distractor they chose: explain what makes it superficially attractive "
        "but ultimately incorrect. Identify the underlying misconception."
    ),
    "mnemonic": (
        "Give the student a practical mnemonic, memory trick, or pattern to remember the key concept. "
        "Make it vivid and clinically relevant. If a well-known nursing mnemonic exists, use it."
    ),
    "beginner": (
        "Explain this as if the student has never seen this concept before. "
        "Use the simplest possible language, concrete everyday examples, and build from basics."
    ),
    "clinical_story": (
        "Create a short 3-4 sentence clinical vignette (fictional patient) that illustrates "
        "why the correct answer is right. Make it realistic and memorable."
    ),
}


def build_followup_prompt(
    question: str,
    options: dict,
    correct_answer: str,
    correct_text: str,
    selected_answer: str | None,
    selected_text: str | None,
    base_explanation: str | None,
    category: str,
    chip: str,
    user_language: str = "en",
) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the follow-up explanation."""

    chip_instruction = CHIP_INSTRUCTIONS.get(chip, CHIP_INSTRUCTIONS["explain_differently"])

    options_text = "\n".join(f"  {k}. {v}" for k, v in (options or {}).items())

    selected_note = ""
    if selected_answer and selected_answer != correct_answer:
        selected_note = (
            f"\nThe student chose: {selected_answer}. {selected_text or ''} "
            "(This was incorrect.)"
        )
    elif selected_answer == correct_answer:
        selected_note = f"\nThe student answered correctly ({selected_answer}), but still wants a deeper explanation."

    lang_instruction = ""
    if user_language and user_language != "en":
        lang_instruction = f"\nRespond in {user_language}. Keep medical terms in their standard form."

    system_prompt = (
        "You are an expert nursing educator specializing in NCLEX-RN preparation. "
        "Your role is to help students truly understand clinical concepts — not just memorize answers. "
        "Responses must be concise (150–250 words max), clinically accurate, and directly useful. "
        "Never repeat the student's mistake back to them judgmentally. Be encouraging."
    )

    user_message = f"""Follow-up explanation request.

QUESTION: {question}

OPTIONS:
{options_text}

Correct answer: {correct_answer}. {correct_text}
{selected_note}
Category: {category}
Base explanation: {base_explanation or "Not available."}

Task: {chip_instruction}{lang_instruction}

Keep your response focused and under 250 words. No need to repeat the full question."""

    return system_prompt, user_message
