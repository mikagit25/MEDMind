"""
Sanitize teacher-created lesson content before it is injected into AI prompts.

When a lesson's text content is used as context for AI answers, a malicious
teacher could embed prompt injection in the lesson body. This module strips
such patterns from the plain-text representation of lesson content before
it reaches the LLM.
"""
import re
import html
from typing import Any

# Patterns to remove from content that will be sent to LLM as context.
# We are NOT sanitizing what's stored in DB — only what's extracted for AI context.
_LLM_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in [
    r"ignore\s+(previous|all|prior)\s+instructions.*",
    r"disregard\s+(previous|all|prior)\s+instructions.*",
    r"you\s+are\s+now\s+a\s+(?!doctor|physician|medical|tutor|expert).*",
    r"<\s*/?\s*system\s*>.*?</?\s*system\s*>",
    r"\[SYSTEM\].*",
    r"\[\[SYSTEM\]\].*",
    r"#{3,}\s*SYSTEM.*",
    r"---+\s*system\s*---+.*",
    r"act\s+as\s+(?!a\s+(doctor|physician|medical|tutor|expert|student)).*",
    r"pretend\s+(you\s+are|to\s+be)\s+(?!a\s+(doctor|physician|medical)).*",
    r"forget\s+(your|all)\s+(instructions|rules|guidelines|prompt).*",
    r"print\s+(your|the)\s+system\s+prompt.*",
    r"reveal\s+your\s+(system\s+)?prompt.*",
]]

# Maximum characters of lesson content to inject as AI context
MAX_CONTEXT_CHARS = 3000


def extract_text_from_content(content: Any) -> str:
    """Extract plain text from a lesson's JSONB content block structure."""
    if isinstance(content, str):
        return content

    if not isinstance(content, dict):
        return ""

    parts = []

    # Block format: {"blocks": [...]}
    blocks = content.get("blocks", [])
    for block in blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type", "")
        if btype == "text":
            parts.append(block.get("content", ""))
        elif btype == "quiz":
            parts.append(block.get("question", ""))
        elif btype == "case":
            parts.append(block.get("presentation", ""))

    # Legacy format: direct fields
    if not parts:
        for field in ("introduction", "theory", "clinical_application", "summary"):
            val = content.get(field)
            if isinstance(val, str) and val.strip():
                parts.append(val)
        objectives = content.get("learning_objectives", [])
        if isinstance(objectives, list):
            parts.extend(o for o in objectives if isinstance(o, str))

    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def sanitize_for_llm_context(content: Any, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Extract lesson text and sanitize it for safe injection into LLM prompts.

    Returns a clean string safe to include in system/user context.
    """
    text = extract_text_from_content(content)
    text = html.unescape(text)

    # Remove injection patterns
    for pattern in _LLM_INJECTION_PATTERNS:
        text = pattern.sub("[content removed]", text)

    # Truncate to max context length
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[... content truncated for context window ...]"

    return text.strip()
