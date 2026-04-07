"""Prompts for generating and validating educational content."""


def generate_module_structure(specialty: str, topic: str, level: str) -> str:
    return (
        f"Create a structured medical education module for:\n"
        f"- Specialty: {specialty}\n"
        f"- Topic: {topic}\n"
        f"- Level: {level}\n\n"
        "Output JSON with:\n"
        '{"meta": {"id": "...", "specialty": "...", "title": "...", "level": "...", '
        '"duration_hours": N, "prerequisite_modules": []}, '
        '"lessons": [{"id": "L001", "title": "...", "order": 1}], '
        '"flashcards": [], "mcq_questions": [], "clinical_cases": []}'
    )


def generate_lesson_content(specialty: str, lesson_title: str, key_concepts: list[str], level: str) -> str:
    concepts_str = ", ".join(key_concepts)
    return (
        f"Generate detailed lesson content for a medical education platform.\n"
        f"Specialty: {specialty}\n"
        f"Lesson title: {lesson_title}\n"
        f"Key concepts to cover: {concepts_str}\n"
        f"Level: {level}\n\n"
        "Output JSON: {\"intro\": \"...\", \"sections\": [{\"heading\": \"...\", \"text\": \"...\"}], "
        "\"clinical_pearl\": \"...\", \"key_points\": [...]}"
    )


def generate_flashcards(specialty: str, topic: str, count: int = 6) -> str:
    return (
        f"Generate {count} high-yield medical flashcards for:\n"
        f"Specialty: {specialty}, Topic: {topic}\n\n"
        'Output JSON array: [{"id": "FC001", "question": "...", "answer": "...", '
        '"difficulty": "easy|medium|hard", "category": "..."}]'
    )


def generate_mcq_questions(specialty: str, topic: str, difficulty: str, count: int = 3) -> str:
    return (
        f"Generate {count} multiple-choice questions (MCQ) for medical education.\n"
        f"Specialty: {specialty}, Topic: {topic}, Difficulty: {difficulty}\n\n"
        'Output JSON array: [{"id": "Q001", "question": "...", '
        '"options": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}, '
        '"correct": "A", "explanation": "...", "difficulty": "medium"}]'
    )


def generate_clinical_case(specialty: str, topic: str, difficulty: str) -> str:
    return (
        f"Generate a clinical case for medical education.\n"
        f"Specialty: {specialty}, Topic: {topic}, Difficulty: {difficulty}\n\n"
        'Output JSON: {"title": "...", "presentation": {"chief_complaint": "...", '
        '"history": "...", "vitals": {}}, "diagnosis": "...", '
        '"management": ["step1", "step2"], "teaching_points": [...]}'
    )


def generate_full_module(specialty: str, topic: str, level: str) -> str:
    """Prompt to generate a complete module JSON (meta + lessons + flashcards + mcq + cases)."""
    return (
        f"You are a medical education expert. Generate a complete, detailed educational module.\n\n"
        f"Specialty: {specialty}\n"
        f"Topic: {topic}\n"
        f"Level: {level}\n\n"
        "Return ONLY valid JSON (no markdown, no explanation) with this exact structure:\n"
        "{\n"
        '  "meta": {\n'
        '    "id": "SPEC-NNN",\n'
        '    "specialty": "' + specialty + '",\n'
        '    "title": "Full module title",\n'
        '    "level": "' + level + '",\n'
        '    "duration_hours": 2,\n'
        '    "prerequisite_modules": []\n'
        "  },\n"
        '  "lessons": [\n'
        '    {\n'
        '      "id": "L001", "title": "Lesson title", "order": 1,\n'
        '      "intro": "Introduction text",\n'
        '      "sections": [{"heading": "Section title", "text": "Detailed content..."}],\n'
        '      "key_points": ["point1", "point2"],\n'
        '      "clinical_pearl": "Clinical pearl text",\n'
        '      "duration_minutes": 20\n'
        "    }\n"
        "  ],\n"
        '  "flashcards": [\n'
        '    {"id": "FC001", "question": "Q?", "answer": "A", "difficulty": "medium", "category": "category"}\n'
        "  ],\n"
        '  "mcq_questions": [\n'
        '    {\n'
        '      "id": "Q001", "question": "Question?",\n'
        '      "options": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."},\n'
        '      "correct": "A", "explanation": "Why A is correct", "difficulty": "medium"\n'
        "    }\n"
        "  ],\n"
        '  "clinical_cases": [\n'
        '    {\n'
        '      "id": "CASE001", "title": "Case title",\n'
        '      "presentation": "Patient presentation text",\n'
        '      "diagnosis": "Primary diagnosis",\n'
        '      "management": ["Step 1", "Step 2"],\n'
        '      "teaching_points": ["Point 1", "Point 2"]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Requirements:\n"
        f"- Generate 3-4 lessons with full content\n"
        f"- Generate 6-8 flashcards\n"
        f"- Generate 3-5 MCQ questions\n"
        f"- Generate 1-2 clinical cases\n"
        f"- All content must be evidence-based and clinically accurate\n"
        f"- Include HIPAA disclaimer where AI outputs are for education only\n"
    )


def validate_medical_content(content: str, content_type: str) -> str:
    return (
        f"Review this medical education content ({content_type}) for accuracy:\n\n"
        f"{content}\n\n"
        "Check:\n"
        "1. Is the medical information evidence-based and accurate?\n"
        "2. Are drug doses and guidelines current (within 2 years)?\n"
        "3. Are there any dangerous errors that could harm a patient if followed?\n"
        "4. Suggest corrections if needed.\n"
        "Output: {\"accurate\": true/false, \"issues\": [...], \"corrections\": [...]}"
    )
