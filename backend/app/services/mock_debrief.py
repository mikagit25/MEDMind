"""V7 Phase 6 — Mock Exam Debrief Service.

Pattern detectors (config-driven, rule-based — no AI).
Each detector is a dict:
  {id, name, description, check_fn(per_question) -> bool}
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Configuration ──────────────────────────────────────────────────────────────

# Minimum questions in a sub-category to trigger a pattern
MIN_CATEGORY_QUESTIONS = 5
# Error rate threshold above which a pattern fires
ERROR_RATE_THRESHOLD = 0.60
# Timing thresholds (seconds)
SLOW_QUESTION_THRESHOLD_S = 180    # 3 minutes = likely re-reading multiple times
EXAM_TIME_PER_Q_NCLEX_S = 72      # NCLEX: 144 min / 120 questions = 72s average

# ── Detector definitions ──────────────────────────────────────────────────────

DETECTORS = [
    {
        "id": "ordered_errors",
        "name": "Priority/Sequence questions",
        "description": (
            "Your error rate on ordered/sequencing questions is significantly higher than your overall score. "
            "These questions test clinical prioritization — always complete your assessment before intervening."
        ),
        "question_types": ["ordered"],
        "min_count": 3,
        "error_threshold": 0.60,
    },
    {
        "id": "calculation_errors",
        "name": "Calculation questions",
        "description": (
            "You missed more than half of calculation questions. "
            "Practice dose calculation step-by-step: identify what's given, what's needed, and use dimensional analysis."
        ),
        "question_types": ["calculation"],
        "min_count": 3,
        "error_threshold": 0.60,
    },
    {
        "id": "sata_errors",
        "name": "Select All That Apply (SATA)",
        "description": (
            "SATA questions had a high error rate. Treat each option independently: "
            "ask 'Is this true for the client?' for each option separately rather than looking for the 'best' answer."
        ),
        "question_types": ["sata"],
        "min_count": 3,
        "error_threshold": 0.65,
    },
    {
        "id": "pharmacology_errors",
        "name": "Pharmacology category",
        "description": (
            "Your pharmacology accuracy is below target. "
            "Focus on: mechanism of action, common side effects, and priority nursing assessments for high-alert drugs."
        ),
        "nclex_categories": ["pharmacological_therapies", "pharmacological"],
        "min_count": 5,
        "error_threshold": 0.55,
    },
    {
        "id": "priority_keyword_errors",
        "name": "Priority/First action questions",
        "description": (
            "Questions containing 'first', 'priority', or 'initial' in the stem had a higher error rate. "
            "For these questions: select assessment over intervention unless the patient is in immediate danger."
        ),
        "keyword_match": ["first", "priority", "initial", "immediately"],
        "min_count": 3,
        "error_threshold": 0.55,
    },
    {
        "id": "infection_control_errors",
        "name": "Infection control / Safety",
        "description": (
            "Infection control questions showed weakness. "
            "Key rule: select Standard Precautions first unless transmission-based precautions are indicated; "
            "know airborne vs droplet vs contact distinctions."
        ),
        "nclex_categories": ["safety_infection_control", "safety"],
        "min_count": 4,
        "error_threshold": 0.55,
    },
    {
        "id": "slow_question_pattern",
        "name": "Time management",
        "description": (
            "You spent more than 3 minutes on several questions. "
            "On the real exam, flag and move on — extended second-guessing rarely improves accuracy. "
            "Trust your first instinct on NCLEX-style questions."
        ),
        "timing_check": True,
        "slow_threshold_s": SLOW_QUESTION_THRESHOLD_S,
        "slow_count_threshold": 5,
    },
]


# ── Detector logic ─────────────────────────────────────────────────────────────

def run_detectors(per_question: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run all detectors against per_question list. Return list of triggered patterns."""
    fired = []

    answered = [pq for pq in per_question if pq.get("correct") is not None]
    if not answered:
        return fired

    overall_errors = sum(1 for pq in answered if not pq["correct"])
    overall_error_rate = overall_errors / len(answered) if answered else 0

    for det in DETECTORS:
        if det.get("timing_check"):
            # Timing-based detector
            slow_qs = [
                pq for pq in per_question
                if (pq.get("time_seconds") or 0) >= det["slow_threshold_s"]
            ]
            if len(slow_qs) >= det["slow_count_threshold"]:
                fired.append({
                    "id": det["id"],
                    "name": det["name"],
                    "description": det["description"],
                    "count": len(slow_qs),
                    "detail": f"{len(slow_qs)} questions took over {det['slow_threshold_s']//60} minutes",
                })
            continue

        if det.get("keyword_match"):
            # Keyword-based detector
            subset = [
                pq for pq in answered
                if any(kw in (pq.get("question_text") or "").lower() for kw in det["keyword_match"])
            ]
        elif det.get("question_types"):
            subset = [pq for pq in answered if pq.get("question_type") in det["question_types"]]
        elif det.get("nclex_categories"):
            subset = [pq for pq in answered if pq.get("nclex_client_needs") in det["nclex_categories"]]
        else:
            continue

        if len(subset) < det.get("min_count", 3):
            continue

        errors_in_subset = sum(1 for pq in subset if not pq["correct"])
        error_rate = errors_in_subset / len(subset)

        # Only fire if error rate is substantially above overall error rate
        if error_rate >= det["error_threshold"] and error_rate > overall_error_rate + 0.10:
            fired.append({
                "id": det["id"],
                "name": det["name"],
                "description": det["description"],
                "error_rate_pct": round(error_rate * 100, 1),
                "count": len(subset),
                "errors": errors_in_subset,
            })

    return fired


def analyze_timing(per_question: List[Dict[str, Any]], exam_mode_id: str = "") -> Dict[str, Any]:
    """Compute timing statistics per question."""
    times = [(pq.get("index", i), pq.get("time_seconds") or 0) for i, pq in enumerate(per_question)]
    valid_times = [t for _, t in times if t > 0]

    if not valid_times:
        return {"available": False}

    avg_time = sum(valid_times) / len(valid_times)
    total_time = sum(valid_times)
    slow_questions = [
        {"index": idx, "time_seconds": t}
        for idx, t in times
        if t >= SLOW_QUESTION_THRESHOLD_S
    ]

    # For NCLEX, estimated allowed time
    expected_time_per_q = EXAM_TIME_PER_Q_NCLEX_S
    questions_over_limit = [
        {"index": idx, "time_seconds": t}
        for idx, t in times
        if t > expected_time_per_q * 2  # 2× average = attention flag
    ]

    return {
        "available": True,
        "avg_time_seconds": round(avg_time, 1),
        "total_time_seconds": round(total_time),
        "slow_questions": slow_questions,
        "questions_over_limit": questions_over_limit,
        "would_exceed_time_limit": (
            total_time > expected_time_per_q * len(per_question) * 1.1
        ),
    }
