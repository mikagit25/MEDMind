"""
Prompt injection guard for medical AI context.

Blocks attempts to override system instructions, exfiltrate prompts, or escape
the medical education context. Uses pattern matching rather than a second LLM
call so the check is fast and deterministic.
"""
import re
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Patterns that indicate prompt injection / jailbreak attempts.
# Compiled once at module load.
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    # Override instructions
    r"ignore\s+(?:previous|prior|all|your)\s+(?:\w+\s+)*instructions",
    r"disregard\s+(?:previous|prior|all|your)\s+(?:\w+\s+)*instructions",
    r"forget\s+(?:your|all)\s+(?:instructions|rules|guidelines|prompt)",
    r"override\s+(?:your|all|previous)\s+(?:instructions|rules|system|prompt|guidelines)",

    # System prompt exfiltration
    r"print\s+(?:your|the)\s+system\s+prompt",
    r"repeat\s+(?:your|the)\s+(?:system\s+)?prompt",
    r"show\s+me\s+your\s+(?:\w+\s+)*(?:prompt|instructions)",
    r"what\s+(?:is|are)\s+your\s+(?:\w+\s+)*instructions",
    r"reveal\s+your\s+(?:\w+\s+)*(?:prompt|instructions)",
    r"output\s+your\s+(?:\w+\s+)*instructions",

    # Role switching / persona hijacking — only block clearly malicious personas
    r"you\s+are\s+now\s+(?:an?\s+)?(?:DAN|evil|harmful|unrestricted|uncensored|different\s+AI|hacker|drug\s+dealer)",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:an?\s+)?(?:evil|harmful|drug\s+dealer|hacker|criminal|unrestricted|uncensored)",
    r"pretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+)?(?:evil|harmful|drug\s+dealer|hacker|criminal|unrestricted|uncensored)",
    r"roleplay\s+as\s+(?:an?\s+)?(?:evil|harmful|drug\s+dealer|hacker|criminal|unrestricted|uncensored)",
    r"simulate\s+(?:being\s+)?(?:an?\s+)?(?:evil|harmful|drug\s+dealer|hacker|criminal|unrestricted|uncensored)",

    # Jailbreak keywords
    r"\bDAN\s+mode\b",
    r"\bdeveloper\s+mode\b",
    r"\bjailbreak\b",
    r"do\s+anything\s+now",
    r"no\s+restrictions\s+mode",

    # Prompt delimiter attacks
    r"<\s*/?\s*system\s*>",
    r"\[SYSTEM\]",
    r"\[\[SYSTEM\]\]",
    r"#{3,}\s*SYSTEM",
    r"---+\s*system\s*---+",
]]

# Maximum allowed message length (characters). Prevents context-stuffing attacks.
MAX_MESSAGE_LENGTH = 4000


def sanitize_ai_message(message: str, field_name: str = "message") -> str:
    """
    Validate and sanitize a user message before sending to AI.

    Raises HTTP 422 if the message contains prompt injection patterns.
    Returns the original message (stripped) if it passes all checks.
    """
    if not message or not message.strip():
        raise HTTPException(status_code=422, detail=f"{field_name} cannot be empty")

    stripped = message.strip()

    if len(stripped) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} exceeds maximum length of {MAX_MESSAGE_LENGTH} characters",
        )

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(stripped):
            raise HTTPException(
                status_code=422,
                detail="Message contains disallowed content. Please ask a medical education question.",
            )

    return stripped
