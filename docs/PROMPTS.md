# MedMind AI — AI Generation Prompts

> Prompts for generating content, system instructions for AI Tutor, and Claude API call templates.

---

## 1. AI TUTOR SYSTEM PROMPTS

### 1.1 Base Tutor Prompt
```
You are MedMind AI, an expert medical education assistant.
Specialty: {specialty}
User level: {user_level} (student/resident/doctor)
Mode: {mode}

Core principles:
- Evidence-based medicine only — cite guidelines (ESC, ACC/AHA, WHO, etc.)
- Accuracy over simplicity — never oversimplify to the point of error
- Clinical context — connect theory to bedside practice
- Use formatted markdown: ### headers, bullet points, **bold** for key terms

{mode_instructions}

{pubmed_context}
```

### 1.2 Mode Instructions

**Tutor mode:**
```
Provide clear, structured explanations. Use ### headers for sections.
Always include: pathophysiology → clinical presentation → diagnosis → management.
End with 2-3 clinical pearls the user should remember.
```

**Socratic mode:**
```
Do NOT give direct answers. Guide the user with targeted questions.
When user answers correctly: validate and build on it.
When user answers incorrectly: ask a clarifying question to help them self-correct.
Never say "wrong" — say "interesting, let's think about that further..."
```

**Case mode:**
```
Present a clinical case step-by-step. Start with chief complaint, age, sex.
Wait for user to request specific information (history, vitals, labs, imaging).
Evaluate their clinical reasoning at each step.
At the end: provide diagnosis, management, teaching points.
```

**Exam mode:**
```
Generate a USMLE Step 2-style question with 5 options (A-E).
After the user answers:
- If correct: explain WHY it's correct + teach a clinical pearl
- If incorrect: explain the correct answer + why their choice was wrong
Then offer next question.
Format: clinical vignette → question stem → options A-E
```

---

## 2. CONTENT GENERATION PROMPTS

### 2.1 Generate Module Structure
```
Create a medical education module structure for:
Specialty: {specialty}
Topic: {topic}
Level: {level} (1=basic, 5=expert)
Target audience: {audience}

Output JSON with this exact structure:
{
  "meta": {
    "id": "{CODE}-{NNN}",
    "specialty": "{specialty}",
    "title": "{title}",
    "title_en": "{title_en}",
    "level": "{level_word}",
    "duration_hours": {number},
    "prerequisite_modules": []
  },
  "lessons": [
    {
      "id": "L001",
      "order": 1,
      "title": "{lesson_title}",
      "content": {
        "intro": "...",
        "sections": [
          {"heading": "...", "text": "..."},
          ...
        ],
        "clinical_pearl": "...",
        "key_points": ["...", "...", "...", "..."]
      }
    }
  ],
  "flashcards": [...],
  "mcq_questions": [...],
  "clinical_cases": [...]
}

Include 3-5 lessons, 5-8 flashcards, 3 MCQ questions, 1 clinical case.
All content must be evidence-based with current guidelines.
```

### 2.2 Generate Flashcards
```
Generate {count} medical education flashcards for:
Topic: {topic}
Specialty: {specialty}
Difficulty: {difficulty} (easy/medium/hard)

Format as JSON array:
[
  {
    "question": "...",
    "answer": "...",
    "difficulty": "medium",
    "category": "{topic}"
  }
]

Rules:
- Questions should test understanding, not pure memorization
- Answers should be concise but complete (2-5 sentences)
- Include mnemonics where helpful
- Cover mechanisms, clinical features, management, guidelines
```

### 2.3 Generate MCQ Questions
```
Generate {count} USMLE-style MCQ questions for:
Topic: {topic}
Specialty: {specialty}
Difficulty: {difficulty}

Format as JSON array:
[
  {
    "question": "Clinical vignette...\n\nWhat is the most appropriate next step?",
    "options": {
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "...",
      "E": "..."
    },
    "correct": "B",
    "explanation": "The correct answer is B because... Option A is wrong because... etc."
  }
]

Rules:
- Use clinical vignettes (patient scenario)
- All distractors should be plausible
- Explanations must address all 5 options
```

### 2.4 Generate Clinical Case
```
Generate an interactive clinical case for:
Specialty: {specialty}
Topic/Diagnosis: {topic}
Difficulty: {difficulty}

Format as JSON:
{
  "title": "...",
  "specialty": "{specialty}",
  "presentation": "Age, sex, chief complaint, brief history...",
  "vitals": {"BP": "...", "HR": "...", "RR": "...", "SpO2": "...", "Temp": "..."},
  "initial_findings": "Physical exam findings...",
  "investigations": {
    "labs": "Key abnormal values...",
    "imaging": "Key findings...",
    "ecg": "If relevant..."
  },
  "diagnosis": "Final diagnosis",
  "differential_diagnosis": ["...", "...", "..."],
  "management": ["Step 1: ...", "Step 2: ...", "..."],
  "teaching_points": ["...", "...", "...", "..."],
  "guidelines_reference": "ESC/ACC/WHO guidelines year..."
}
```

### 2.5 Onboarding Welcome Plan
```
Create a personalized learning plan for a new MedMind user:
Role: {role}
Goal: {goal}
Specialties: {specialties}
Daily time: {minutes} minutes/day

Return JSON:
{
  "welcome_message": "Personal greeting...",
  "first_24h": ["Task 1...", "Task 2...", "Task 3..."],
  "week1_focus": "Description of week 1 learning focus...",
  "week2_preview": "What to expect in week 2...",
  "success_criteria": "What success looks like in 30 days...",
  "recommended_modules": ["MODULE-001", "MODULE-002"],
  "daily_schedule_suggestion": "Morning: X, Evening: Y..."
}
```

---

## 3. DRUG DATABASE PROMPTS

### 3.1 Generate Drug Profile
```
Create a comprehensive drug profile for: {drug_name}
Specialty context: {specialty}

Return JSON:
{
  "name": "...",
  "generic_name": "...",
  "drug_class": "...",
  "mechanism": "...",
  "indications": ["...", "..."],
  "contraindications": ["...", "..."],
  "dosing": {
    "standard": "...",
    "renal_adjustment": "...",
    "hepatic_adjustment": "..."
  },
  "adverse_effects": {
    "common": ["...", "..."],
    "serious": ["...", "..."],
    "black_box": null
  },
  "interactions": ["...", "..."],
  "monitoring": ["...", "..."],
  "clinical_pearls": ["...", "..."],
  "high_yield": true/false,
  "nti": true/false
}
```

---

## 4. VETERINARY PROMPTS

### 4.1 Adapt Human Content to Veterinary
```
Adapt this human medical content for veterinary use:
Species: {species}
Original content: {human_content}

Important differences to address:
- Species-specific anatomy/physiology variations
- Different normal ranges (HR, RR, temp, etc.)
- Contraindicated drugs in this species
- Different dosing protocols
- Species-specific diseases and presentations

Return the adapted content in the same JSON format.
```

### 4.2 Generate Veterinary Drug Dosing
```
Provide evidence-based drug dosing information for:
Drug: {drug_name}
Species: {species}

Return JSON:
{
  "drug": "{drug_name}",
  "species": "{species}",
  "dose": "...",
  "route": "IV/IM/PO/SC",
  "frequency": "...",
  "notes": "...",
  "contraindications": ["..."],
  "warnings": ["..."],
  "references": "..."
}
```

---

## 5. CONTENT VALIDATION PROMPT

```
Review this medical education content for accuracy:
Content type: {type} (lesson/flashcard/mcq/case)
Specialty: {specialty}
Content: {content}

Check for:
1. Clinical accuracy — are facts correct per current guidelines?
2. Outdated information — any guidelines changed recently?
3. Dangerous errors — anything that could harm if followed?
4. Missing critical info — essential points omitted?

Return JSON:
{
  "is_accurate": true/false,
  "confidence": 0.0-1.0,
  "issues": [
    {"severity": "critical/major/minor", "description": "...", "correction": "..."}
  ],
  "last_guideline_update": "Year/organization",
  "approved": true/false
}
```
