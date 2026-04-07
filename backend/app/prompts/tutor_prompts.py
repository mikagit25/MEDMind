"""AI tutor prompt templates."""

HIPAA_DISCLAIMER = (
    "\n\n---\n"
    "⚕️ *Educational tool only. Not a diagnostic instrument. "
    "All AI responses require verification by a licensed clinician.*"
)


def tutor_system_prompt(user_level: str = "intermediate", specialty: str | None = None) -> str:
    specialty_line = f" specialising in {specialty}" if specialty else ""
    return (
        f"You are MedMind AI — an expert medical educator{specialty_line}. "
        "Your role is to teach, not to diagnose. "
        "You adapt your explanations to the learner's level, use evidence-based medicine (EBM), "
        "cite clinical guidelines (ESC, AHA, WHO, NICE), and always add a HIPAA disclaimer "
        "reminding the user that your responses are educational only. "
        f"The user's level is: {user_level}. "
        "Be concise, use mnemonics where helpful, and highlight 'clinical pearls'."
    )


def explain_concept_prompt(concept: str, level: str, context: str | None) -> str:
    ctx_line = f"\nContext: the user is currently studying: {context}" if context else ""
    return (
        f"Explain the medical concept: **{concept}**\n"
        f"Learner level: {level}{ctx_line}\n\n"
        "Structure your response:\n"
        "1. **Definition** — one sentence\n"
        "2. **Mechanism / Pathophysiology** — key points\n"
        "3. **Clinical relevance** — why it matters in practice\n"
        "4. **Clinical pearl** — one memorable takeaway\n"
        "5. **Common exam pitfall** — what students often get wrong\n"
        + HIPAA_DISCLAIMER
    )


def quiz_mode_prompt(topic: str, difficulty: str, previous_mistakes: list[str]) -> str:
    mistakes_line = ""
    if previous_mistakes:
        mistakes_line = f"\nFocus especially on these areas where the student has struggled: {', '.join(previous_mistakes)}"

    return (
        f"You are conducting an oral examination on: **{topic}**\n"
        f"Difficulty: {difficulty}{mistakes_line}\n\n"
        "Ask 3 progressively harder questions. After each question, wait for the student's answer "
        "(they will respond in the next message). "
        "Start with the first question now. "
        "Format: **Question 1:** [your question]"
        + HIPAA_DISCLAIMER
    )


def case_discussion_prompt(
    case_data: dict,
    user_decision: str,
    discussion_point: str | None,
) -> str:
    point_line = f"\nSpecific discussion point: {discussion_point}" if discussion_point else ""
    return (
        f"Clinical Case Discussion\n\n"
        f"**Case:** {case_data.get('title', 'Unknown')}\n"
        f"**Presentation:** {case_data.get('presentation', '')}\n"
        f"**Correct diagnosis:** {case_data.get('diagnosis', '')}\n"
        f"**Standard management:** {'; '.join(case_data.get('management', []))}\n\n"
        f"**Student's decision/answer:** {user_decision}{point_line}\n\n"
        "Evaluate the student's decision:\n"
        "- Is it correct? If not, explain why.\n"
        "- What did they get right?\n"
        "- What important steps did they miss?\n"
        "- What is the key teaching point from this case?\n"
        + HIPAA_DISCLAIMER
    )
