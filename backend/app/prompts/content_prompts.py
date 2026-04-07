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
