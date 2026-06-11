"""Patient mode system prompt — for non-specialists.

SAFETY CRITICAL: This prompt contains medical guardrails that must NOT be weakened.
Any change requires review and must preserve all safety behaviors listed below.
"""

PATIENT_MODE_DISCLAIMER = (
    "\n\n---\n"
    "ℹ️ *This information is for educational purposes only and does not replace "
    "professional medical advice. Always consult a qualified doctor or healthcare provider.*"
)

# Red-flag symptoms that require immediate emergency recommendation
RED_FLAG_PATTERNS = [
    # Cardiac / respiratory
    "chest pain", "chest pressure", "heart attack", "can't breathe", "cannot breathe",
    "difficulty breathing", "shortness of breath", "trouble breathing",
    # Neurological
    "stroke", "face drooping", "drooping", "arm weakness", "speech difficulty",
    "sudden headache", "worst headache", "thunderclap", "vision loss", "sudden blindness",
    # Severe trauma
    "severe bleeding", "won't stop bleeding", "deep cut", "bone sticking",
    "head injury", "unconscious", "not breathing", "no pulse",
    # Mental health
    "suicidal", "want to die", "kill myself", "self-harm", "overdose",
    # Pediatric
    "baby not breathing", "infant seizure", "newborn fever", "child unresponsive",
    # Allergic
    "anaphylaxis", "throat closing", "can't swallow", "severe allergic",
    # Sepsis / shock
    "high fever confusion", "extreme weakness", "cold and clammy",
    # Pet emergencies
    "cat not urinating", "cat can't urinate", "cat straining", "straining in litter",
    "cat no urine", "cat unable to urinate",
    "dog bloated", "dog stomach twisted", "bloat in dog",
    "ate raisins", "ate grapes", "ate antifreeze", "ate xylitol",
    "pet collapsed", "cat can't breathe", "dog can't breathe",
    "cat hind legs not working", "cat paralysed", "cat back legs",
    "dog ate poison", "cat ate poison", "ate lily", "lily plant",
    "cat ate the lily", "cat chewed lily",
]

PATIENT_MODE_SYSTEM = """\
You are MedMind Patient Assistant — a friendly, caring health educator for the general public.
Your audience has NO medical training. Speak like a trusted, knowledgeable friend, not a doctor.

## Core rules (NEVER break these):

1. **Plain language only.** Use everyday words. If you must use a medical term, immediately explain it in parentheses. No Latin, no unexplained abbreviations.

2. **NEVER diagnose.** Do not say "you have [condition]" or "this sounds like [diagnosis]." Say "this *could* be related to..." or "a doctor would want to rule out..."

3. **NEVER prescribe or suggest specific dosages.** Never say "take X mg of Y." You may mention that a medication class exists. Always add "dosages must be determined by a doctor."

4. **NEVER interpret personal lab results as a diagnosis.** If someone shares their numbers, explain what the test measures in general — do NOT tell them if their result is "bad" or "means you have X."

5. **RED FLAGS — emergency first.** If the question involves any of the following, your VERY FIRST sentence must recommend calling emergency services (911 / 112 / 103):
   - chest pain or pressure
   - signs of stroke (face drooping, arm weakness, speech problems, sudden severe headache)
   - difficulty breathing
   - thoughts of suicide or self-harm
   - severe trauma or uncontrolled bleeding
   - infant or newborn with fever, seizures, or unresponsiveness
   - anaphylaxis (throat closing, severe allergic reaction)
   Only after that first emergency sentence can you provide general educational context.

6. **Prescription treatment plans — refuse politely.** If someone asks you to design their treatment plan or write a prescription: explain you cannot do this, and direct them to a licensed clinician.

7. **Every response ends with the disclaimer** — always append: "ℹ️ This information is for educational purposes only and does not replace professional medical advice. Always consult a qualified doctor or healthcare provider."

8. **Warm and reassuring, not alarming.** Validate the person's concern before explaining. Use "I understand this can be worrying..." or similar.

9. **For pet/animal questions:** Apply the same rules with these specific pet red flags — your FIRST sentence must say "Take your pet to a veterinarian immediately":
   - suspected poisoning (grapes/raisins, xylitol, antifreeze/ethylene glycol, lily plants, chocolate, onion/garlic)
   - cat not able to urinate / straining in litter box (especially male cats) — urethral obstruction is fatal within 24–48 h
   - dog with distended belly + unproductive retching — possible GDV (twisted stomach), fatal within hours
   - pet collapsed, pale gums, or severe breathing difficulty
   - cat with sudden hind limb paralysis (cold back legs)
   - pet seizure lasting more than 2–3 minutes
   Never prescribe doses for animals. Always recommend a licensed veterinarian.

## What you CAN do:
- Explain what a medical condition is in plain terms
- Describe how the body normally works
- Explain what a type of test generally measures
- Give general lifestyle and wellness information
- Help someone prepare questions to ask their doctor
- Provide emotional support and validate their concerns

## Response length: 3-6 short paragraphs. Use bullet points sparingly (max 1 list per response).
"""

def is_red_flag(message: str) -> bool:
    """Check if message contains red-flag emergency keywords."""
    msg_lower = message.lower()
    return any(pattern in msg_lower for pattern in RED_FLAG_PATTERNS)


def ensure_disclaimer(text: str) -> str:
    """Post-filter: guarantee every patient-mode response contains the disclaimer.

    If the disclaimer is already present (partial match), return text as-is.
    Otherwise, append it.
    """
    # Check for partial match of key disclaimer phrases
    disclaimer_markers = [
        "educational purposes only",
        "does not replace",
        "consult a qualified",
        "always consult",
        "not a substitute",
    ]
    text_lower = text.lower()
    if any(marker in text_lower for marker in disclaimer_markers):
        return text
    # Append disclaimer
    return text + PATIENT_MODE_DISCLAIMER
