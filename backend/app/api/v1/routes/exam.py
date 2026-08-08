"""Board Exam Prep Mode — USMLE / NCLEX / UKMLA / Gulf Prometric.

Timed sessions with DB-persisted state, CAT-lite difficulty adaptation,
and NCLEX category analytics.

Endpoints
─────────
GET  /exam/modes                         — list available modes
POST /exam/sessions                      — create timed session
GET  /exam/sessions/{id}                 — get session + questions
POST /exam/sessions/{id}/answer          — record answer
POST /exam/sessions/{id}/submit          — finalize + results
GET  /exam/sessions/{id}/results         — results + category breakdown
GET  /exam/history                       — past sessions
GET  /exam/nclex/analytics               — NCLEX category performance over time
GET  /exam/nclex/readiness               — NCLEX Readiness Score (weighted estimate)
GET  /exam/definitions                   — exam registry (public, active only)
GET  /exam/definitions/{slug}            — single exam definition
GET  /exam/definitions/family/{family}   — all exams in a family (e.g. gulf)
"""

import uuid as uuid_lib
from datetime import datetime, timedelta, date as date_type
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import ExamDefinition, ExamSession, ExamPlan, ExamPlanCompletion, MCQQuestion, Module, QuestionStats, QuestionAttempt, User
from app.services.ai_router import call_claude_structured, call_ollama_structured
from app.services.billing import user_has_exam_access, is_gulf_exam
from app.services import study_planner as planner

router = APIRouter(prefix="/exam", tags=["exam"])

# ── Exam mode definitions ──────────────────────────────────────────────────────

EXAM_MODES = [
    {
        "id": "usmle_step1",
        "name": "USMLE Step 1",
        "description": "Basic sciences — 40 questions, 60 min",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": False,
        "difficulty": "hard",
        "icon": "stethoscope",
        "pass_threshold": 60,
    },
    {
        "id": "usmle_step2",
        "name": "USMLE Step 2 CK",
        "description": "Clinical knowledge — 40 questions, 60 min",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": False,
        "difficulty": "hard",
        "icon": "hospital",
        "pass_threshold": 60,
    },
    {
        "id": "nclex_rn_75",
        "name": "NCLEX-RN (75 questions)",
        "description": "Minimum-length NCLEX simulation — 75 questions, 90 min. Nursing questions only.",
        "questions": 75,
        "duration_min": 90,
        "nursing_only": True,
        "difficulty": None,  # CAT adapts difficulty
        "cat": True,
        "icon": "heart-pulse",
        "pass_threshold": 62,
    },
    {
        "id": "nclex_rn_85",
        "name": "NCLEX-RN (85 questions)",
        "description": "Standard NCLEX simulation — 85 questions, 105 min.",
        "questions": 85,
        "duration_min": 105,
        "nursing_only": True,
        "difficulty": None,
        "cat": True,
        "icon": "heart-pulse",
        "pass_threshold": 62,
    },
    {
        "id": "nclex_rn_145",
        "name": "NCLEX-RN (145 questions)",
        "description": "Maximum-length NCLEX simulation — 145 questions, 210 min.",
        "questions": 145,
        "duration_min": 210,
        "nursing_only": True,
        "difficulty": None,
        "cat": True,
        "icon": "heart-pulse",
        "pass_threshold": 62,
    },
    {
        "id": "nclex_category",
        "name": "NCLEX by Category",
        "description": "Practice 30 questions from a single NCLEX client-needs category.",
        "questions": 30,
        "duration_min": 45,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "layers",
        "pass_threshold": 60,
    },
    {
        "id": "ukmla",
        "name": "UKMLA / MLA",
        "description": "UK licensing — 30 questions, 45 min",
        "questions": 30,
        "duration_min": 45,
        "nursing_only": False,
        "difficulty": "medium",
        "cat": False,
        "icon": "flag",
        "pass_threshold": 60,
    },
    {
        "id": "quick_20",
        "name": "Quick Practice",
        "description": "20 mixed questions, 20 min — any level",
        "questions": 20,
        "duration_min": 20,
        "nursing_only": False,
        "difficulty": None,
        "cat": False,
        "icon": "zap",
        "pass_threshold": 60,
    },
    {
        "id": "nclex_demo",
        "name": "NCLEX Demo (Free)",
        "description": "Try 10 NCLEX-style nursing questions — no subscription needed.",
        "questions": 10,
        "duration_min": 15,
        "nursing_only": True,
        "difficulty": "medium",
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 60,
        "demo": True,
    },
    # ── Gulf Prometric exam modes (G1) ─────────────────────────────────────────
    # Requires gulf_bundle, pro, clinic, or lifetime tier. Free/student = locked.
    {
        "id": "snle_practice",
        "name": "SNLE Practice",
        "description": "Saudi Nursing Licensing Exam — 50 blueprint-weighted questions, 75 min.",
        "questions": 50,
        "duration_min": 75,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "snle",
    },
    {
        "id": "dha_practice",
        "name": "DHA Practice",
        "description": "Dubai Health Authority Nursing Exam — 40 questions, 60 min.",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "dha",
    },
    {
        "id": "qchp_practice",
        "name": "QCHP Practice",
        "description": "Qatar Council for Healthcare Practitioners — 40 questions, 60 min.",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "qchp",
    },
    {
        "id": "omsb_practice",
        "name": "OMSB Practice",
        "description": "Oman Medical Specialty Board Nursing Exam — 40 questions, 60 min.",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "omsb",
    },
    {
        "id": "nhra_practice",
        "name": "NHRA Practice",
        "description": "National Health Regulatory Authority (Bahrain) — 40 questions, 60 min.",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "nhra",
    },
    {
        "id": "mohuae_practice",
        "name": "MOH UAE Practice",
        "description": "Ministry of Health UAE Nursing Exam — 40 questions, 60 min.",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "mohuae",
    },
    {
        "id": "haad_practice",
        "name": "DOH/HAAD Practice",
        "description": "Department of Health Abu Dhabi Nursing Exam — 40 questions, 60 min.",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "haad",
    },
    # ── Gulf Full Simulations (official exam length) ───────────────────────────
    # SNLE: 200 questions, 3 hours (source: SCFHS Applicant Guide 2024)
    {
        "id": "snle_full",
        "name": "SNLE Full Simulation",
        "description": "Saudi Nursing Licensing Exam — Full 200-question simulation, 3 hours. Matches real exam format.",
        "questions": 200,
        "duration_min": 180,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "snle",
        "full_simulation": True,
    },
    {
        "id": "dha_full",
        "name": "DHA Full Simulation",
        "description": "Dubai Health Authority — Full 100-question simulation, 2 hours.",
        "questions": 100,
        "duration_min": 120,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "dha",
        "full_simulation": True,
    },
    {
        "id": "qchp_full",
        "name": "QCHP Full Simulation",
        "description": "Qatar Council for Healthcare Practitioners — Full 100-question simulation, 2 hours.",
        "questions": 100,
        "duration_min": 120,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "qchp",
        "full_simulation": True,
    },
    {
        "id": "omsb_full",
        "name": "OMSB Full Simulation",
        "description": "Oman Medical Specialty Board — Full 100-question simulation, 2 hours.",
        "questions": 100,
        "duration_min": 120,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "omsb",
        "full_simulation": True,
    },
    {
        "id": "nhra_full",
        "name": "NHRA Full Simulation",
        "description": "National Health Regulatory Authority Bahrain — Full 100-question simulation, 2 hours.",
        "questions": 100,
        "duration_min": 120,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "nhra",
        "full_simulation": True,
    },
    {
        "id": "mohuae_full",
        "name": "MOH UAE Full Simulation",
        "description": "Ministry of Health UAE — Full 100-question simulation, 2 hours.",
        "questions": 100,
        "duration_min": 120,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "mohuae",
        "full_simulation": True,
    },
    {
        "id": "haad_full",
        "name": "DOH/HAAD Full Simulation",
        "description": "Department of Health Abu Dhabi — Full 100-question simulation, 2 hours.",
        "questions": 100,
        "duration_min": 120,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 65,
        "gulf": True,
        "exam_slug": "haad",
        "full_simulation": True,
    },
]

NCLEX_CLIENT_NEEDS = [
    "safe_effective_care",
    "health_promotion",
    "psychosocial",
    "basic_care",
    "pharmacological",
    "reduction_risk",
    "physiological_adaptation",
]

NCLEX_CLIENT_NEEDS_LABELS = {
    # ── Canonical 7 NCLEX client-needs categories ──────────────────────────────
    "safe_effective_care": "Safe & Effective Care Environment",
    "health_promotion": "Health Promotion & Maintenance",
    "psychosocial": "Psychosocial Integrity",
    "basic_care": "Basic Care & Comfort",
    "pharmacological": "Pharmacological & Parenteral Therapies",
    "reduction_risk": "Reduction of Risk Potential",
    "physiological_adaptation": "Physiological Adaptation",
    # ── Common aliases found in generated question banks ────────────────────────
    "safe_effective_care_environment": "Safe & Effective Care Environment",
    "safety": "Safe & Effective Care Environment",
    "safety_infection_control": "Safe & Effective Care Environment",
    "management_of_care": "Safe & Effective Care Environment",
    "psychological": "Psychosocial Integrity",
    "psychological_integrity": "Psychosocial Integrity",
    "psychosocial_integrity": "Psychosocial Integrity",
    "communication": "Psychosocial Integrity",
    "physiological": "Physiological Adaptation",
    "physiological_integrity": "Physiological Adaptation",
    "basic_care_and_comfort": "Basic Care & Comfort",
    "pharmacological_therapies": "Pharmacological & Parenteral Therapies",
    "pharmacological_and_parenteral": "Pharmacological & Parenteral Therapies",
    "reduction_of_risk": "Reduction of Risk Potential",
    "reduction_of_risk_potential": "Reduction of Risk Potential",
    "health_promotion_and_maintenance": "Health Promotion & Maintenance",
    "health_promotion_maintenance": "Health Promotion & Maintenance",
    "safe_effective": "Safe & Effective Care Environment",
    "psychological_adaptation": "Physiological Adaptation",
    "communication_and_documentation": "Psychosocial Integrity",
    "comfort": "Basic Care & Comfort",
}

CJMM_LABELS = {
    "recognize_cues": "Recognize Cues",
    "analyze_cues": "Analyze Cues",
    "prioritize_hypotheses": "Prioritize Hypotheses",
    "generate_solutions": "Generate Solutions",
    "take_actions": "Take Actions",
    "evaluate_outcomes": "Evaluate Outcomes",
}

# Aliases found in AI-generated question banks → canonical CJMM key
_CJMM_ALIAS_TO_CANONICAL: dict[str, str] = {
    # recognize_cues
    "assess": "recognize_cues",
    "assess_client": "recognize_cues",
    "assess_situations": "recognize_cues",
    "recognize_deterioration": "recognize_cues",
    # analyze_cues
    "analyze_data": "analyze_cues",
    "analyze": "analyze_cues",
    # prioritize_hypotheses
    "diagnose": "prioritize_hypotheses",
    "prioritize": "prioritize_hypotheses",
    "develop_plan": "generate_solutions",
    "develop_care_plan": "generate_solutions",
    # generate_solutions
    "plan": "generate_solutions",
    "apply_knowledge": "generate_solutions",
    "calculate_doses": "generate_solutions",
    "teach_patient": "generate_solutions",
    # take_actions
    "intervene": "take_actions",
    "administer_medication": "take_actions",
    "maintain_function": "take_actions",
    "follow_policies": "take_actions",
    "communicate": "take_actions",
    "communicate_effectively": "take_actions",
    "report": "take_actions",
    "document": "take_actions",
    "document_client_info": "take_actions",
    "inform_client": "take_actions",
    "inform": "take_actions",
    # evaluate_outcomes
    "evaluate": "evaluate_outcomes",
}

# Alias → canonical NCLEX key (built automatically from NCLEX_CLIENT_NEEDS_LABELS)
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _alias, _label in NCLEX_CLIENT_NEEDS_LABELS.items():
    if _alias not in NCLEX_CLIENT_NEEDS:
        for _canonical in NCLEX_CLIENT_NEEDS:
            if NCLEX_CLIENT_NEEDS_LABELS[_canonical] == _label:
                _ALIAS_TO_CANONICAL[_alias] = _canonical
                break

# CAT difficulty levels in order
CAT_DIFFICULTY_LADDER = ["easy", "medium", "hard"]


# ── Schemas ────────────────────────────────────────────────────────────────────

class StartSession(BaseModel):
    mode_id: str
    nclex_category: Optional[str] = None  # for nclex_category mode
    question_ids: Optional[List[str]] = None  # for retry-wrong sessions


class AnswerBody(BaseModel):
    question_index: int
    selected_option: str = ""
    selected_options: List[str] = []
    ordered_options: List[str] = []
    numeric_value: Optional[float] = None
    time_seconds: Optional[float] = None   # V7: time spent on this question


class FlagBody(BaseModel):
    reason: str = ""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _score_question(q_data: dict, answer: Any) -> tuple[bool, str]:
    """Score one question. Returns (is_correct, display_of_correct_answer)."""
    qtype = q_data.get("question_type", "mcq")
    if qtype == "sata":
        submitted = sorted(s.upper() for s in (answer or []))
        correct = sorted(s.upper() for s in (q_data.get("_correct_answers") or []))
        return submitted == correct, ",".join(correct)
    elif qtype == "ordered":
        submitted = [s.upper() for s in (answer or [])]
        correct = [s.upper() for s in (q_data.get("_correct_order") or [])]
        return submitted == correct, "→".join(correct)
    elif qtype == "calculation":
        num_ans = q_data.get("_numeric_answer")
        tol = q_data.get("_numeric_tolerance") or 0.5
        unit = q_data.get("numeric_unit") or ""
        if answer is None or num_ans is None:
            return False, f"{num_ans} {unit}".strip()
        return abs(float(answer) - float(num_ans)) <= tol, f"{num_ans} {unit}".strip()
    else:
        correct = q_data.get("_correct", "")
        return str(answer or "").upper() == str(correct).upper(), correct


def _next_cat_difficulty(current: str, was_correct: bool) -> str:
    idx = CAT_DIFFICULTY_LADDER.index(current) if current in CAT_DIFFICULTY_LADDER else 1
    if was_correct:
        idx = min(idx + 1, len(CAT_DIFFICULTY_LADDER) - 1)
    else:
        idx = max(idx - 1, 0)
    return CAT_DIFFICULTY_LADDER[idx]


def _build_results(sess: ExamSession, questions_data: list) -> dict:
    answers = sess.answers or {}
    total = len(questions_data)
    correct_count = 0
    answered_count = 0
    wrong_list = []
    all_questions_list = []
    per_q = []
    category_stats: dict[str, dict] = {}
    cjmm_stats: dict[str, dict] = {}

    for q in questions_data:
        idx = str(q["index"])
        answer = answers.get(idx)

        # Normalize category/skill early (used for both answered and unanswered)
        cat = q.get("nclex_client_needs")
        if cat:
            cat = _ALIAS_TO_CANONICAL.get(cat, cat)
        skill = q.get("cjmm_skill")
        if skill:
            skill = _CJMM_ALIAS_TO_CANONICAL.get(skill, skill)

        if answer is None:
            # Unanswered (skipped) — show in All tab as neutral, exclude from score
            all_questions_list.append({
                "index": q["index"],
                "id": q.get("id"),
                "question": q["question"],
                "options": q.get("options"),
                "your_answer": None,
                "correct_answer": q.get("_correct") or "",
                "correct": None,  # null = skipped, distinct from False = wrong
                "explanation": q.get("explanation"),
                "rationales": q.get("_rationales"),
                "key_takeaway": q.get("_key_takeaway"),
                "test_taking_tip": q.get("_test_taking_tip"),
                "rationales_es": q.get("_rationales_es"),
                "key_takeaway_es": q.get("_key_takeaway_es"),
                "test_taking_tip_es": q.get("_test_taking_tip_es"),
                "explanation_es": q.get("_explanation_es"),
                "explanation_ar": q.get("_explanation_ar"),
                "rationales_ar": q.get("_rationales_ar"),
                "key_takeaway_ar": q.get("_key_takeaway_ar"),
                "test_taking_tip_ar": q.get("_test_taking_tip_ar"),
                "nclex_client_needs": cat,
                "cjmm_skill": skill,
                "source_refs": q.get("_source_refs") or [],
            })
            per_q.append({
                "index": q["index"],
                "question_id": q.get("id"),
                "correct": None,
                "selected": None,
                "correct_answer": None,
                "nclex_client_needs": cat,
                "cjmm_skill": skill,
                "difficulty": q.get("difficulty", "medium") or "medium",
                "question_type": q.get("question_type", "mcq"),
                "ngn_type": q.get("ngn_type"),
                "time_seconds": answers.get(f"{q['index']}_time"),
            })
            continue

        answered_count += 1
        is_correct, correct_display = _score_question(q, answer)

        if is_correct:
            correct_count += 1

        # Category tracking (only for answered questions)
        if cat:
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "correct": 0, "label": NCLEX_CLIENT_NEEDS_LABELS.get(cat, cat)}
            category_stats[cat]["total"] += 1
            if is_correct:
                category_stats[cat]["correct"] += 1

        # CJMM tracking (only for answered questions)
        if skill:
            if skill not in cjmm_stats:
                cjmm_stats[skill] = {"total": 0, "correct": 0, "label": CJMM_LABELS.get(skill, skill)}
            cjmm_stats[skill]["total"] += 1
            if is_correct:
                cjmm_stats[skill]["correct"] += 1

        q_full = {
            "index": q["index"],
            "id": q.get("id"),
            "question": q["question"],
            "options": q.get("options"),
            "your_answer": answer,
            "correct_answer": correct_display,
            "correct": is_correct,
            "explanation": q.get("explanation"),
            "rationales": q.get("_rationales"),
            "key_takeaway": q.get("_key_takeaway"),
            "test_taking_tip": q.get("_test_taking_tip"),
            "rationales_es": q.get("_rationales_es"),
            "key_takeaway_es": q.get("_key_takeaway_es"),
            "test_taking_tip_es": q.get("_test_taking_tip_es"),
            "explanation_es": q.get("_explanation_es"),
            "explanation_ar": q.get("_explanation_ar"),
            "rationales_ar": q.get("_rationales_ar"),
            "key_takeaway_ar": q.get("_key_takeaway_ar"),
            "test_taking_tip_ar": q.get("_test_taking_tip_ar"),
            "nclex_client_needs": cat,
            "cjmm_skill": skill,
            "source_refs": q.get("_source_refs") or [],
        }
        all_questions_list.append(q_full)
        if not is_correct:
            wrong_list.append(q_full)

        per_q.append({
            "index": q["index"],
            "question_id": q.get("id"),
            "correct": is_correct,
            "selected": answer,
            "correct_answer": correct_display if not is_correct else None,
            "nclex_client_needs": cat,
            "cjmm_skill": skill,
            "difficulty": q.get("difficulty", "medium") or "medium",
            "question_type": q.get("question_type", "mcq"),
            "ngn_type": q.get("ngn_type"),
            "time_seconds": answers.get(f"{q['index']}_time"),
        })

    mode = next((m for m in EXAM_MODES if m["id"] == sess.mode_id), {})
    pass_threshold = mode.get("pass_threshold", 60)
    unanswered_count = total - answered_count
    # Score is based only on answered questions (skipped don't penalize)
    score_pct = round((correct_count / answered_count) * 100) if answered_count else 0
    passed = score_pct >= pass_threshold

    # Category pct
    for c in category_stats.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0
    for c in cjmm_stats.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0

    # Weak categories (pct < 60%)
    weak_categories = [
        {"key": k, **v} for k, v in category_stats.items() if v["pct"] < 60
    ]
    weak_categories.sort(key=lambda x: x["pct"])

    start = sess.starts_at
    end = sess.ends_at if sess.status == "completed" else datetime.utcnow()
    time_taken_min = round((end - start).total_seconds() / 60, 1)

    return {
        "session_id": str(sess.id),
        "mode": sess.mode_name,
        "mode_id": sess.mode_id,
        "total_questions": total,
        "answered": answered_count,
        "unanswered": unanswered_count,
        "correct": correct_count,
        "wrong": answered_count - correct_count,
        "score_pct": score_pct,
        "passed": passed,
        "pass_threshold": pass_threshold,
        "time_taken_min": time_taken_min,
        "cat_enabled": sess.cat_enabled,
        "per_question": per_q,
        "wrong_questions": wrong_list,
        "all_questions": all_questions_list,
        "nclex_category_breakdown": category_stats,
        "nclex_cjmm_breakdown": cjmm_stats,
        "weak_categories": weak_categories,
        "message": (
            "Excellent — NCLEX-ready performance!" if score_pct >= 75
            else "Good progress! Focus on the weak categories below." if passed
            else "Keep practicing — review the weak areas and try again!"
        ),
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/modes")
async def list_modes(user: User = Depends(get_current_user)):
    result = []
    is_free = user.subscription_tier == "free"
    for m in EXAM_MODES:
        is_demo = m.get("demo", False)
        is_gulf = m.get("gulf", False)
        exam_slug = m.get("exam_slug")
        if is_gulf and exam_slug:
            has_access = user_has_exam_access(user, exam_slug)
            locked = not has_access
            lock_reason = (
                "Gulf Bundle or Pro subscription required to access Gulf Prometric exams."
                if locked else None
            )
        else:
            locked = is_free and not is_demo
            lock_reason = "Upgrade to Student or Pro to unlock board exams" if locked else None
        result.append({**m, "locked": locked, "lock_reason": lock_reason})
    return result


@router.get("/nclex/categories")
async def nclex_categories():
    """Return NCLEX client-needs categories for the category-practice mode."""
    return [
        {"key": k, "label": NCLEX_CLIENT_NEEDS_LABELS[k]}
        for k in NCLEX_CLIENT_NEEDS
    ]


@router.post("/sessions", status_code=201)
async def create_session(
    body: StartSession,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mode = next((m for m in EXAM_MODES if m["id"] == body.mode_id), None)
    if not mode:
        raise HTTPException(404, f"Unknown exam mode: {body.mode_id}")

    if not mode.get("demo", False) and user.subscription_tier == "free":
        raise HTTPException(403, "Board Exam mode requires a Student or Pro subscription.")

    # Gulf exam access control: requires gulf_bundle, pro, clinic, or lifetime tier
    if mode.get("gulf", False):
        exam_slug = mode.get("exam_slug", "")
        if not user_has_exam_access(user, exam_slug):
            raise HTTPException(
                403,
                "Gulf Prometric exams require a Gulf Bundle or Pro subscription. "
                "Upgrade at /pricing to unlock all 7 Gulf exams."
            )

    cat_mode = mode.get("cat", False)
    nursing_only = mode.get("nursing_only", False)
    start_difficulty = "medium"

    # Retry-wrong mode: fetch specific question IDs directly
    if body.question_ids:
        try:
            qid_uuids = [uuid_lib.UUID(qid) for qid in body.question_ids]
        except ValueError:
            raise HTTPException(400, "Invalid question ID format")
        mcqs = (await db.execute(
            select(MCQQuestion).where(MCQQuestion.id.in_(qid_uuids))
        )).scalars().all()
        cat_mode = False
    else:
        # Build query normally — only active questions (V7: retired questions excluded)
        q = select(MCQQuestion).where(MCQQuestion.status == "active")

        if nursing_only:
            q = q.join(Module, Module.id == MCQQuestion.module_id).where(
                Module.is_nursing == True,
                Module.is_published == True,
            )

        # Gulf mode: filter by exam-specific slug; fall back to all nursing questions if insufficient
        if mode.get("gulf") and (exam_slug := mode.get("exam_slug")):
            import json as _json
            from sqlalchemy import literal as sa_literal
            from sqlalchemy.dialects.postgresql import JSONB
            q_gulf = q.where(
                MCQQuestion.exam_slugs.op("@>")(sa_literal(_json.dumps([exam_slug])).cast(JSONB))
            ).where(
                # L2 quarantine: exclude jurisdiction-sensitive questions not yet verified for any profile
                (MCQQuestion.jurisdiction_sensitive.is_(False))
                | (MCQQuestion.jurisdiction_sensitive.is_(None))
                | (MCQQuestion.jurisdiction_verified_for.isnot(None))
            ).order_by(func.random()).limit(mode["questions"])
            gulf_mcqs = (await db.execute(q_gulf)).scalars().all()
            if len(gulf_mcqs) >= mode["questions"]:
                mcqs = gulf_mcqs
                cat_mode = False
                # skip remainder of query block
                goto_session = True
            else:
                # Not enough exam-specific questions — fall back to full nursing pool
                logger.warning("Gulf exam %s: only %d tagged questions, falling back to nursing pool",
                               exam_slug, len(gulf_mcqs))
                # q already has nursing_only filter applied above; just proceed
                goto_session = False
        else:
            goto_session = False

        if not goto_session:
            if body.mode_id == "nclex_category" and body.nclex_category:
                if body.nclex_category not in NCLEX_CLIENT_NEEDS:
                    raise HTTPException(400, f"Unknown NCLEX category: {body.nclex_category}")
                canonical = body.nclex_category
                all_values = [canonical] + [
                    alias for alias, canon in _ALIAS_TO_CANONICAL.items() if canon == canonical
                ]
                q = q.where(MCQQuestion.nclex_client_needs.in_(all_values))
            elif not cat_mode and mode.get("difficulty"):
                # V7: prefer computed_difficulty when calibrated, fall back to static difficulty
                from app.models.models import QuestionStats
                from sqlalchemy import case as sa_case, or_ as sa_or
                target_diff = mode["difficulty"]
                q = q.outerjoin(
                    QuestionStats,
                    (QuestionStats.question_id == MCQQuestion.id) & (QuestionStats.exam_slug == None)
                ).where(
                    sa_case(
                        (QuestionStats.sample_size_ok == True, QuestionStats.computed_difficulty),
                        else_=MCQQuestion.difficulty,
                    ) == target_diff
                )

            if cat_mode:
                # V7: CAT also uses effective difficulty
                from app.models.models import QuestionStats
                from sqlalchemy import case as sa_case
                q = q.outerjoin(
                    QuestionStats,
                    (QuestionStats.question_id == MCQQuestion.id) & (QuestionStats.exam_slug == None)
                ).where(
                    sa_case(
                        (QuestionStats.sample_size_ok == True, QuestionStats.computed_difficulty),
                        else_=MCQQuestion.difficulty,
                    ) == start_difficulty
                )

            q = q.order_by(func.random()).limit(mode["questions"])
            mcqs = (await db.execute(q)).scalars().all()

    if len(mcqs) < 1:
        raise HTTPException(
            503,
            "Not enough questions available for this exam mode. "
            "The question bank is still growing — check back soon!"
        )

    now = datetime.utcnow()
    ends_at = now + timedelta(minutes=mode["duration_min"])

    question_ids = [str(mcq.id) for mcq in mcqs]
    questions_snapshot = [
        {
            "index": i,
            "id": str(mcq.id),
            "question": mcq.question,
            "options": mcq.options if isinstance(mcq.options, dict) else {},
            "question_type": getattr(mcq, "question_type", "mcq") or "mcq",
            "numeric_unit": getattr(mcq, "numeric_unit", None),
            "ngn_type": getattr(mcq, "ngn_type", None),
            "bowtie_data": getattr(mcq, "bowtie_data", None),
            "nclex_client_needs": getattr(mcq, "nclex_client_needs", None),
            "cjmm_skill": getattr(mcq, "cjmm_skill", None),
            "difficulty": getattr(mcq, "difficulty", "medium") or "medium",
            "explanation": getattr(mcq, "explanation", None),
            # private scoring fields (filtered from public session view)
            "_correct": mcq.correct,
            "_correct_answers": getattr(mcq, "correct_answers", None),
            "_correct_order": getattr(mcq, "correct_order", None),
            "_numeric_answer": getattr(mcq, "numeric_answer", None),
            "_numeric_tolerance": getattr(mcq, "numeric_tolerance", 0.5) or 0.5,
            # private until session completed (reveals correct option via 'why' field)
            "_rationales": getattr(mcq, "rationales", None),
            "_key_takeaway": getattr(mcq, "key_takeaway", None),
            "_test_taking_tip": getattr(mcq, "test_taking_tip", None),
            # G2: Spanish translations (null if not yet translated)
            "_rationales_es": getattr(mcq, "rationales_es", None),
            "_key_takeaway_es": getattr(mcq, "key_takeaway_es", None),
            "_test_taking_tip_es": getattr(mcq, "test_taking_tip_es", None),
            "_explanation_es": getattr(mcq, "explanation_es", None),
            # Arabic translations for Gulf exams (null if not yet translated)
            "_explanation_ar": getattr(mcq, "explanation_ar", None),
            "_rationales_ar": getattr(mcq, "rationales_ar", None),
            "_key_takeaway_ar": getattr(mcq, "key_takeaway_ar", None),
            "_test_taking_tip_ar": getattr(mcq, "test_taking_tip_ar", None),
            # Source references — shown in rationale panel after answering
            "_source_refs": getattr(mcq, "source_refs", None) or [],
        }
        for i, mcq in enumerate(mcqs)
    ]

    session = ExamSession(
        id=uuid_lib.uuid4(),
        user_id=user.id,
        mode_id=body.mode_id,
        mode_name=mode["name"],
        status="active",
        question_ids=question_ids,
        answers={},
        total_questions=len(mcqs),
        duration_min=mode["duration_min"],
        starts_at=now,
        ends_at=ends_at,
        current_difficulty=start_difficulty,
        cat_enabled=cat_mode,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Return without private answer fields
    public_questions = [
        {k: v for k, v in q_.items() if not k.startswith("_")}
        for q_ in questions_snapshot
    ]

    # Store full snapshot in session cache (Redis in production; here we'll use per-session JSONB)
    # We re-fetch questions when needed from the question_ids list
    session.answers = {"_snapshot": questions_snapshot}  # store snapshot for scoring
    await db.commit()

    return {
        "session_id": str(session.id),
        "mode": mode["name"],
        "mode_id": body.mode_id,
        "total_questions": len(mcqs),
        "duration_min": mode["duration_min"],
        "ends_at": ends_at.isoformat() + "Z",
        "cat_enabled": cat_mode,
        "questions": public_questions,
        "nclex_category_filter": body.nclex_category,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)

    snapshot = (sess.answers or {}).get("_snapshot", [])
    answered_indices = [k for k in (sess.answers or {}) if k != "_snapshot"]
    time_left = max(0, int((sess.ends_at - datetime.utcnow()).total_seconds()))

    public_questions = [
        {k: v for k, v in q_.items() if not k.startswith("_")}
        for q_ in snapshot
    ]

    return {
        "session_id": session_id,
        "mode": sess.mode_name,
        "mode_id": sess.mode_id,
        "status": sess.status,
        "questions": public_questions,
        "answered_indices": answered_indices,
        "time_left_seconds": time_left,
        "ends_at": sess.ends_at.isoformat() + "Z",
        "cat_enabled": sess.cat_enabled,
        "current_difficulty": sess.current_difficulty,
        "total_questions": sess.total_questions,
        "duration_min": sess.duration_min,
    }


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: str,
    body: AnswerBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)
    if sess.status != "active":
        raise HTTPException(400, "Session is not active")
    if datetime.utcnow() > sess.ends_at:
        sess.status = "expired"
        await db.commit()
        raise HTTPException(400, "Session time has expired")

    snapshot = (sess.answers or {}).get("_snapshot", [])
    idx = body.question_index
    if idx < 0 or idx >= len(snapshot):
        raise HTTPException(400, "Invalid question index")

    qtype = snapshot[idx].get("question_type", "mcq")
    if qtype == "sata":
        answer = body.selected_options
    elif qtype == "ordered":
        answer = body.ordered_options
    elif qtype == "calculation":
        answer = body.numeric_value
    else:
        answer = body.selected_option

    # CAT: adjust difficulty based on answer correctness
    new_difficulty = sess.current_difficulty
    if sess.cat_enabled:
        is_correct, _ = _score_question(snapshot[idx], answer)
        new_difficulty = _next_cat_difficulty(sess.current_difficulty, is_correct)

    # Merge answer into the answers dict (keep _snapshot)
    answers = dict(sess.answers or {})
    answers[str(idx)] = answer
    if body.time_seconds is not None:
        answers[f"{idx}_time"] = round(body.time_seconds, 2)
    if sess.cat_enabled:
        sess.current_difficulty = new_difficulty
    sess.answers = answers
    await db.commit()

    # Return rationale for the answered question (safe: user already answered)
    q_snap = snapshot[idx]
    return {
        "recorded": True,
        "question_index": idx,
        "current_difficulty": new_difficulty if sess.cat_enabled else None,
        "explanation": q_snap.get("explanation"),
        "rationales": q_snap.get("_rationales"),
        "key_takeaway": q_snap.get("_key_takeaway"),
        "test_taking_tip": q_snap.get("_test_taking_tip"),
        # G2: Spanish translations (null when not yet translated)
        "rationales_es": q_snap.get("_rationales_es"),
        "key_takeaway_es": q_snap.get("_key_takeaway_es"),
        "test_taking_tip_es": q_snap.get("_test_taking_tip_es"),
        "explanation_es": q_snap.get("_explanation_es"),
        # Arabic translations for Gulf exams (null when not yet translated)
        "explanation_ar": q_snap.get("_explanation_ar"),
        "rationales_ar": q_snap.get("_rationales_ar"),
        "key_takeaway_ar": q_snap.get("_key_takeaway_ar"),
        "test_taking_tip_ar": q_snap.get("_test_taking_tip_ar"),
        # Source references for clinical verification
        "source_refs": q_snap.get("_source_refs") or [],
        # Correct answer letter — used for option color highlighting in practice mode
        "correct_answer": q_snap.get("_correct"),
    }


@router.post("/sessions/{session_id}/submit")
async def finalize_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)
    if sess.status == "completed":
        snapshot = (sess.answers or {}).get("_snapshot", [])
        return _build_results(sess, snapshot)

    snapshot = (sess.answers or {}).get("_snapshot", [])
    results = _build_results(sess, snapshot)

    now = datetime.utcnow()
    sess.status = "completed"
    sess.ends_at = min(sess.ends_at, now)
    sess.correct = results["correct"]
    sess.wrong = results["wrong"]
    sess.score_pct = results["score_pct"]
    sess.passed = results["passed"]
    sess.time_taken_min = results["time_taken_min"]
    sess.per_question = results["per_question"]
    await db.commit()

    # Invalidate readiness cache so next GET /nclex/readiness reflects this session
    if sess.mode_id.startswith("nclex_"):
        from app.services.readiness import invalidate_readiness_cache
        await invalidate_readiness_cache(user.id)

    # V7: record per-question attempts for psychometrics (best-effort, don't fail submit)
    try:
        from app.services.psychometrics import record_attempt
        mode_obj = next((m for m in EXAM_MODES if m["id"] == sess.mode_id), {})
        exam_slug = mode_obj.get("exam_slug")
        session_type = "exam" if mode_obj.get("timed") else "practice"
        if "mock" in sess.mode_id:
            session_type = "mock"
        for pq in (results.get("per_question") or []):
            qid = pq.get("question_id")
            if not qid or pq.get("correct") is None:
                continue  # skip unanswered/skipped questions
            await record_attempt(
                db=db,
                question_id=qid,
                user_id=str(user.id),
                is_correct=bool(pq["correct"]),
                selected=pq.get("selected"),
                session_id=str(sess.id),
                session_type=session_type,
                exam_slug=exam_slug,
                time_seconds=pq.get("time_seconds"),
            )
        await db.commit()
    except Exception as _e:
        logger.warning("psychometrics record_attempt failed: %s", _e)

    return results


@router.get("/sessions/{session_id}/results")
async def get_results(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)
    if sess.status not in ("completed", "expired"):
        raise HTTPException(400, "Session not yet submitted")
    snapshot = (sess.answers or {}).get("_snapshot", [])
    return _build_results(sess, snapshot)


@router.get("/history")
async def exam_history(
    limit: int = Query(20, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.user_id == user.id,
            ExamSession.status.in_(["completed", "expired"]),
        )
        .order_by(ExamSession.created_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": str(s.id),
            "mode": s.mode_name,
            "mode_id": s.mode_id,
            "started_at": s.starts_at.isoformat(),
            "score_pct": s.score_pct,
            "passed": s.passed,
            "correct": s.correct,
            "total_questions": s.total_questions,
            "time_taken_min": s.time_taken_min,
            "cat_enabled": s.cat_enabled,
        }
        for s in sessions
    ]


@router.get("/nclex/analytics")
async def nclex_analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate NCLEX category performance across all completed sessions."""
    result = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.user_id == user.id,
            ExamSession.status == "completed",
            ExamSession.mode_id.like("nclex_%"),
        )
        .order_by(ExamSession.created_at.desc())
        .limit(10)
    )
    sessions = result.scalars().all()

    if not sessions:
        return {"sessions_analyzed": 0, "category_performance": {}, "cjmm_performance": {}}

    # Aggregate per_question data across sessions
    category_totals: dict[str, dict] = {}
    cjmm_totals: dict[str, dict] = {}

    for sess in sessions:
        for pq in (sess.per_question or []):
            cat = pq.get("nclex_client_needs")
            skill = pq.get("cjmm_skill")
            is_correct = pq.get("correct", False)

            if cat:
                cat = _ALIAS_TO_CANONICAL.get(cat, cat)
                if cat not in category_totals:
                    category_totals[cat] = {"total": 0, "correct": 0, "label": NCLEX_CLIENT_NEEDS_LABELS.get(cat, cat)}
                category_totals[cat]["total"] += 1
                if is_correct:
                    category_totals[cat]["correct"] += 1

            if skill:
                skill = _CJMM_ALIAS_TO_CANONICAL.get(skill, skill)
                if skill not in cjmm_totals:
                    cjmm_totals[skill] = {"total": 0, "correct": 0, "label": CJMM_LABELS.get(skill, skill)}
                cjmm_totals[skill]["total"] += 1
                if is_correct:
                    cjmm_totals[skill]["correct"] += 1

    for c in category_totals.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0
    for c in cjmm_totals.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0

    weak = [{"key": k, **v} for k, v in category_totals.items() if v["pct"] < 60]
    weak.sort(key=lambda x: x["pct"])

    return {
        "sessions_analyzed": len(sessions),
        "category_performance": category_totals,
        "cjmm_performance": cjmm_totals,
        "weak_categories": weak[:3],
        "overall_trend": [
            {
                "session_id": str(s.id),
                "date": s.starts_at.isoformat(),
                "score_pct": s.score_pct,
                "mode": s.mode_name,
            }
            for s in sessions
        ],
    }


@router.get("/gulf/analytics")
async def gulf_analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate Gulf exam performance across all completed sessions — score trend, difficulty, per-exam breakdown."""
    result = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.user_id == user.id,
            ExamSession.status == "completed",
            ExamSession.mode_id.like("gulf_%"),
        )
        .order_by(ExamSession.created_at.desc())
        .limit(20)
    )
    sessions = result.scalars().all()

    if not sessions:
        return {
            "sessions_analyzed": 0,
            "difficulty_performance": {},
            "exam_performance": {},
            "weak_areas": [],
            "overall_trend": [],
        }

    # Difficulty breakdown
    diff_totals: dict[str, dict] = {}
    # Per-exam-mode breakdown
    exam_totals: dict[str, dict] = {}

    GULF_EXAM_LABELS = {
        "snle": "SNLE (Saudi)",
        "dha": "DHA (Dubai)",
        "qchp": "QCHP (Qatar)",
        "omsb": "OMSB (Oman)",
        "nhra": "NHRA (Bahrain)",
        "mohuae": "MOH UAE",
        "haad": "HAAD (Abu Dhabi)",
    }
    DIFF_LABELS = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}

    for sess in sessions:
        # Per-exam aggregation using mode_id suffix
        mode_parts = (sess.mode_id or "").split("_")
        exam_slug = mode_parts[1] if len(mode_parts) >= 2 else "unknown"
        label = GULF_EXAM_LABELS.get(exam_slug, exam_slug.upper())
        if exam_slug not in exam_totals:
            exam_totals[exam_slug] = {"total": 0, "passed": 0, "label": label, "sessions": 0, "avg_score": 0}
        exam_totals[exam_slug]["sessions"] += 1
        if sess.score_pct is not None:
            exam_totals[exam_slug]["total"] += sess.score_pct
            exam_totals[exam_slug]["passed"] += 1 if (sess.passed or False) else 0

        # Difficulty from per_question
        for pq in (sess.per_question or []):
            if pq.get("correct") is None:
                continue
            diff = pq.get("difficulty", "medium") or "medium"
            if diff not in diff_totals:
                diff_totals[diff] = {"total": 0, "correct": 0, "label": DIFF_LABELS.get(diff, diff.title())}
            diff_totals[diff]["total"] += 1
            if pq.get("correct"):
                diff_totals[diff]["correct"] += 1

    for e in exam_totals.values():
        e["avg_score"] = round(e["total"] / e["sessions"]) if e["sessions"] else 0
        del e["total"]

    for d in diff_totals.values():
        d["pct"] = round(d["correct"] / d["total"] * 100) if d["total"] else 0

    weak = [{"key": k, **v} for k, v in diff_totals.items() if v.get("pct", 100) < 60]
    weak.sort(key=lambda x: x.get("pct", 0))

    return {
        "sessions_analyzed": len(sessions),
        "difficulty_performance": diff_totals,
        "exam_performance": exam_totals,
        "weak_areas": weak,
        "overall_trend": [
            {
                "session_id": str(s.id),
                "date": (s.starts_at or s.created_at).strftime("%b %d"),
                "score_pct": s.score_pct,
                "mode": s.mode_name,
                "passed": s.passed,
            }
            for s in reversed(sessions[:10])
        ],
    }


@router.get("/nclex/readiness")
async def get_nclex_readiness(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    NCLEX Readiness Score — weighted accuracy estimate across all practice sessions.

    Weights: NCLEX category distribution × recency (7d/30d/older) × difficulty.
    Minimum 50 answered questions to show a score.

    Legal: this is a practice performance estimate, NOT a NCLEX exam outcome prediction.
    """
    from app.services.readiness import get_cached_readiness
    return await get_cached_readiness(user.id, db)


@router.get("/gulf/readiness")
async def get_gulf_readiness(
    exam_slug: str = "snle",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Gulf Prometric Readiness Score — weighted accuracy estimate for Gulf nursing exams.

    Based on Gulf Prometric blueprint category weights (Med-Surg 23%, Fundamentals 15%, etc.)
    Minimum 30 answered questions to show a score.

    Legal: this is a practice performance estimate, NOT a Gulf exam outcome prediction.
    """
    valid_slugs = {"snle", "dha", "qchp", "omsb", "nhra", "mohuae", "haad"}
    if exam_slug not in valid_slugs:
        raise HTTPException(400, f"Unknown Gulf exam slug. Valid: {', '.join(valid_slugs)}")
    if not user_has_exam_access(user, exam_slug):
        raise HTTPException(403, "Gulf exam readiness requires a Gulf Bundle or Pro subscription.")
    from app.services.readiness import get_cached_gulf_readiness
    return await get_cached_gulf_readiness(user.id, exam_slug, db)


async def _get_session(
    session_id: str, user_id: UUID, db: AsyncSession
) -> ExamSession:
    try:
        sid = uuid_lib.UUID(session_id)
    except ValueError:
        raise HTTPException(404, "Session not found")
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.id == sid,
            ExamSession.user_id == user_id,
        )
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(404, "Session not found")
    return sess


# ── AI Explanation Endpoint ────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    question_id: Optional[str] = None   # ignored — id comes from URL path
    user_question: Optional[str] = None  # optional follow-up from user


@router.post("/questions/{question_id}/explain")
async def explain_question(
    question_id: str,
    body: ExplainRequest = ExplainRequest(question_id=""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI-powered deep explanation for a given MCQ question.

    Uses Claude Haiku (fast + cheap). No AI quota deducted — educational feature.
    """
    try:
        qid = uuid_lib.UUID(question_id)
    except ValueError:
        raise HTTPException(404, "Question not found")

    result = await db.execute(select(MCQQuestion).where(MCQQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")

    # Build options text
    options = q.options or {}
    options_text = "\n".join(f"  {k}. {v}" for k, v in options.items())

    # Correct answer display
    if q.question_type == "sata":
        correct_display = ", ".join(q.correct_answers or [])
        answer_label = f"Correct answers: {correct_display} (Select All That Apply)"
    elif q.question_type == "ordered":
        correct_display = " → ".join(q.correct_order or [])
        answer_label = f"Correct order: {correct_display}"
    elif q.question_type == "calculation":
        answer_label = f"Correct answer: {q.numeric_answer} {q.numeric_unit or ''}"
    else:
        opt_text = options.get(q.correct or "", "")
        answer_label = f"Correct answer: {q.correct}. {opt_text}"

    nclex_cat = NCLEX_CLIENT_NEEDS_LABELS.get(q.nclex_client_needs or "", q.nclex_client_needs or "General Nursing")
    cjmm = CJMM_LABELS.get(q.cjmm_skill or "", "")

    follow_up = f"\n\nStudent's additional question: {body.user_question}" if body.user_question else ""

    system_prompt = (
        "You are an expert NCLEX-RN nursing educator with 20 years of clinical and teaching experience. "
        "Your explanations are clear, clinically accurate, and help students deeply understand the reasoning — "
        "not just memorize answers. Use plain English. Structure your response with clear sections."
    )

    user_msg = f"""NCLEX question explanation request.

QUESTION: {q.question}

OPTIONS: {options_text if options_text else '(Numeric entry)'}

{answer_label}

Category: {nclex_cat}{f' | Skill: {cjmm}' if cjmm else ''}
Base explanation: {q.explanation or 'None.'}
{follow_up}

Explain concisely:
1. Why the correct answer is right (clinical reasoning).
2. Why each wrong option is incorrect (one sentence each)."""

    try:
        explanation, _ = await call_ollama_structured(
            system=system_prompt,
            user_message=user_msg,
            max_tokens=400,
        )
    except Exception as e:
        raise HTTPException(503, f"AI service temporarily unavailable: {str(e)[:100]}")

    return {
        "question_id": question_id,
        "explanation": explanation,
        "nclex_category": nclex_cat,
        "cjmm_skill": cjmm,
    }


class FollowupRequest(BaseModel):
    chip: str = "explain_differently"  # explain_differently|why_not_distractor|mnemonic|beginner|clinical_story
    selected_answer: Optional[str] = None  # what the student picked
    language: Optional[str] = "en"


FOLLOWUP_CHIPS = {
    "explain_differently", "why_not_distractor", "mnemonic", "beginner", "clinical_story"
}


@router.post("/questions/{question_id}/followup")
async def question_followup(
    question_id: str,
    body: FollowupRequest = FollowupRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI follow-up explanation for a question (Phase 4).

    Counts against the user's daily AI quota. Uses Claude Haiku.
    Tracks follow_up_count and flags questions that frequently need re-explanation.
    """
    from app.api.v1.routes.ai import check_ai_rate_limit
    await check_ai_rate_limit(user, db)

    if body.chip not in FOLLOWUP_CHIPS:
        raise HTTPException(422, f"Unknown chip: {body.chip}. Valid: {sorted(FOLLOWUP_CHIPS)}")

    try:
        qid = uuid_lib.UUID(question_id)
    except ValueError:
        raise HTTPException(404, "Question not found")

    result = await db.execute(select(MCQQuestion).where(MCQQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")

    from app.prompts.question_followup import build_followup_prompt
    from app.core.config import settings as _cfg

    options = q.options or {}
    correct_text = options.get(q.correct, "")
    selected_text = options.get(body.selected_answer or "", "") if body.selected_answer else None
    category = NCLEX_CLIENT_NEEDS_LABELS.get(q.nclex_client_needs or "", "General Nursing")

    system_prompt, user_message = build_followup_prompt(
        question=q.question,
        options=options,
        correct_answer=q.correct,
        correct_text=correct_text,
        selected_answer=body.selected_answer,
        selected_text=selected_text,
        base_explanation=q.explanation,
        category=category,
        chip=body.chip,
        user_language=body.language or "en",
    )

    try:
        explanation, _ = await call_ollama_structured(
            system=system_prompt,
            user_message=user_message,
            max_tokens=350,
        )
    except Exception as e:
        raise HTTPException(503, f"AI service temporarily unavailable: {str(e)[:100]}")

    # Track follow-up count and flag if threshold exceeded
    q.follow_up_count = (q.follow_up_count or 0) + 1
    if q.follow_up_count >= _cfg.PSYCHO_FOLLOWUP_THRESHOLD:
        # Import here to avoid circular import
        from app.models.models import QuestionStats
        stats_row = (await db.execute(
            select(QuestionStats).where(QuestionStats.question_id == qid)
        )).scalar_one_or_none()
        if stats_row and stats_row.health not in ("retired", "key_suspect"):
            stats_row.health = "key_suspect"
            db.add(stats_row)

    db.add(q)
    await db.commit()

    return {
        "question_id": question_id,
        "chip": body.chip,
        "explanation": explanation,
        "follow_up_count": q.follow_up_count,
    }


@router.post("/questions/{question_id}/flag")
async def flag_question(
    question_id: str,
    body: FlagBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flag a question as unclear or containing an error."""
    try:
        qid = uuid_lib.UUID(question_id)
    except ValueError:
        raise HTTPException(404, "Question not found")

    result = await db.execute(select(MCQQuestion).where(MCQQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")

    q.is_flagged = True
    q.flag_reason = (body.reason.strip() or None)
    await db.commit()
    return {"flagged": True, "question_id": question_id}


@router.get("/admin/flagged-questions")
async def list_flagged_questions(
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list questions flagged by users."""
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin access required")

    result = await db.execute(
        select(MCQQuestion)
        .where(MCQQuestion.is_flagged.is_(True))
        .order_by(MCQQuestion.created_at.desc())
        .limit(limit)
    )
    questions = result.scalars().all()

    return [
        {
            "id": str(q.id),
            "question": q.question[:200],
            "question_type": q.question_type,
            "flag_reason": q.flag_reason,
            "module_id": str(q.module_id),
            "difficulty": q.difficulty,
            "nclex_client_needs": q.nclex_client_needs,
            "has_rationales": q.rationales is not None,
        }
        for q in questions
    ]


@router.post("/admin/flagged-questions/{question_id}/resolve")
async def resolve_flagged_question(
    question_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin: clear the flag on a question."""
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin access required")

    try:
        qid = uuid_lib.UUID(question_id)
    except ValueError:
        raise HTTPException(404, "Question not found")

    result = await db.execute(select(MCQQuestion).where(MCQQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")

    q.is_flagged = False
    q.flag_reason = None
    await db.commit()
    return {"resolved": True, "question_id": question_id}


# ── Study Plan endpoints (V6 Phase 4) ─────────────────────────────────────────

class CreatePlanBody(BaseModel):
    exam_date: str           # "YYYY-MM-DD"
    daily_minutes: int = 30  # 15 | 30 | 60
    exam_type: str = "nclex"


class CompleteTodayBody(BaseModel):
    task_type: str = "practice"


def _plan_to_response(plan_row: ExamPlan, completions: list) -> dict:
    completed_dates = [c.task_date.date().isoformat() for c in completions]
    tasks = plan_row.plan_cache or planner.generate_plan(
        plan_row.exam_date.date(),
        plan_row.daily_minutes,
    )
    today_task = planner.get_today_task(tasks)
    week_tasks = planner.get_week_tasks(tasks)
    progress = planner.compute_progress(tasks, completed_dates)
    return {
        "id": str(plan_row.id),
        "exam_type": plan_row.exam_type,
        "exam_date": plan_row.exam_date.date().isoformat(),
        "daily_minutes": plan_row.daily_minutes,
        "status": plan_row.status,
        "today_task": today_task,
        "week_tasks": week_tasks,
        "full_plan": tasks,
        "completed_dates": completed_dates,
        "progress": progress,
    }


@router.get("/plan")
async def get_plan(
    exam_type: str = "nclex",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExamPlan)
        .where(ExamPlan.user_id == user.id, ExamPlan.exam_type == exam_type,
               ExamPlan.status == "active")
    )
    plan_row = result.scalar_one_or_none()
    if not plan_row:
        return {"plan": None}

    comps = await db.execute(
        select(ExamPlanCompletion).where(ExamPlanCompletion.plan_id == plan_row.id)
    )
    completions = comps.scalars().all()
    return {"plan": _plan_to_response(plan_row, completions)}


@router.post("/plan")
async def create_plan(
    body: CreatePlanBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        exam_date = date_type.fromisoformat(body.exam_date)
    except ValueError:
        raise HTTPException(400, "exam_date must be YYYY-MM-DD")

    if exam_date <= date_type.today():
        raise HTTPException(400, "exam_date must be in the future")

    if body.daily_minutes not in (15, 30, 60):
        raise HTTPException(400, "daily_minutes must be 15, 30, or 60")

    # Upsert: return existing active plan if one already exists for this user+exam_type.
    # This makes POST idempotent — repeated calls don't create duplicates.
    # To change exam_date / daily_minutes use PATCH /plan.
    existing_result = await db.execute(
        select(ExamPlan)
        .where(ExamPlan.user_id == user.id, ExamPlan.exam_type == body.exam_type,
               ExamPlan.status == "active")
    )
    existing_plan = existing_result.scalar_one_or_none()
    if existing_plan:
        comps = await db.execute(
            select(ExamPlanCompletion).where(ExamPlanCompletion.plan_id == existing_plan.id)
        )
        return {"plan": _plan_to_response(existing_plan, comps.scalars().all())}

    tasks = planner.generate_plan(exam_date, body.daily_minutes)
    plan_row = ExamPlan(
        user_id=user.id,
        exam_type=body.exam_type,
        exam_date=datetime.combine(exam_date, datetime.min.time()),
        daily_minutes=body.daily_minutes,
        status="active",
        plan_cache=tasks,
    )
    db.add(plan_row)
    await db.commit()
    await db.refresh(plan_row)

    comps = await db.execute(
        select(ExamPlanCompletion).where(ExamPlanCompletion.plan_id == plan_row.id)
    )
    return {"plan": _plan_to_response(plan_row, comps.scalars().all())}


@router.post("/plan/complete-today")
async def complete_today(
    body: CompleteTodayBody,
    exam_type: str = Query("nclex"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExamPlan)
        .where(ExamPlan.user_id == user.id, ExamPlan.exam_type == exam_type,
               ExamPlan.status == "active")
    )
    plan_row = result.scalar_one_or_none()
    if not plan_row:
        raise HTTPException(404, "No active plan found")

    today = datetime.combine(date_type.today(), datetime.min.time())

    # Idempotent — ignore duplicate
    existing = await db.execute(
        select(ExamPlanCompletion)
        .where(ExamPlanCompletion.plan_id == plan_row.id,
               ExamPlanCompletion.task_date == today)
    )
    if existing.scalar_one_or_none():
        return {"already_completed": True}

    comp = ExamPlanCompletion(
        plan_id=plan_row.id,
        task_date=today,
        task_type=body.task_type,
    )
    db.add(comp)
    await db.commit()
    return {"completed": True, "date": date_type.today().isoformat()}


@router.delete("/plan")
async def delete_plan(
    exam_type: str = Query("nclex"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExamPlan)
        .where(ExamPlan.user_id == user.id, ExamPlan.exam_type == exam_type,
               ExamPlan.status == "active")
    )
    plan_row = result.scalar_one_or_none()
    if not plan_row:
        raise HTTPException(404, "No active plan found")

    plan_row.status = "abandoned"
    await db.commit()
    return {"deleted": True}


@router.patch("/plan")
async def update_plan_date(
    body: CreatePlanBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reschedule: update exam_date (and optionally daily_minutes) on active plan."""
    try:
        new_date = date_type.fromisoformat(body.exam_date)
    except ValueError:
        raise HTTPException(400, "exam_date must be YYYY-MM-DD")

    if new_date <= date_type.today():
        raise HTTPException(400, "exam_date must be in the future")

    if body.daily_minutes not in (15, 30, 60):
        raise HTTPException(400, "daily_minutes must be 15, 30, or 60")

    result = await db.execute(
        select(ExamPlan)
        .where(ExamPlan.user_id == user.id, ExamPlan.exam_type == body.exam_type,
               ExamPlan.status == "active")
    )
    plan_row = result.scalar_one_or_none()
    if not plan_row:
        raise HTTPException(404, "No active plan found")

    plan_row.exam_date = datetime.combine(new_date, datetime.min.time())
    plan_row.daily_minutes = body.daily_minutes
    plan_row.plan_cache = planner.generate_plan(new_date, body.daily_minutes)
    # flag_modified is required for JSONB columns so SQLAlchemy detects the mutation
    flag_modified(plan_row, "plan_cache")
    await db.commit()
    # refresh required — without it, expired attributes cause MissingGreenlet in async context
    await db.refresh(plan_row)

    comps = await db.execute(
        select(ExamPlanCompletion).where(ExamPlanCompletion.plan_id == plan_row.id)
    )
    return {"plan": _plan_to_response(plan_row, comps.scalars().all())}


# ── Exam Registry endpoints (G1) ──────────────────────────────────────────────

def _exam_def_to_dict(e: ExamDefinition) -> dict:
    return {
        "slug":                 e.slug,
        "name":                 e.name,
        "country":              e.country,
        "regulatory_body":      e.regulatory_body,
        "question_count":       e.question_count,
        "duration_min":         e.duration_min,
        "pass_threshold":       e.pass_threshold,
        "passing_score_label":  e.passing_score_label,
        "blueprint_source":     e.blueprint_source,
        "blueprint_verified_at": e.blueprint_verified_at,
        "status":               e.status,
        "locale":               e.locale,
        "family":               e.family,
        "options_per_question": e.options_per_question,
        "categories":           e.categories or [],
        "exam_date_fixed":      e.exam_date_fixed,
        "disclaimer":           e.disclaimer,
        "stale_blueprint":      _is_stale_blueprint(e.blueprint_verified_at),
        "marketing_ready":      getattr(e, "marketing_ready", False),
    }


def _is_stale_blueprint(verified_at: str | None) -> bool:
    """True if blueprint_verified_at is older than 12 months or missing."""
    if not verified_at:
        return True
    try:
        from datetime import date
        v = date.fromisoformat(verified_at)
        return (date.today() - v).days > 365
    except ValueError:
        return True


@router.get("/definitions", tags=["exam"])
async def list_exam_definitions(
    family: Optional[str] = None,
    include_draft: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Public exam registry. By default returns only active entries.
    Pass include_draft=true (admin use) to see draft entries too."""
    q = select(ExamDefinition)
    if family:
        q = q.where(ExamDefinition.family == family)
    if not include_draft:
        q = q.where(ExamDefinition.status == "active")
    result = await db.execute(q)
    exams = result.scalars().all()
    return [_exam_def_to_dict(e) for e in exams]


@router.get("/definitions/family/{family}", tags=["exam"])
async def list_exam_family(
    family: str,
    include_draft: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """All exams in a family (e.g. 'gulf'). Active only by default."""
    q = select(ExamDefinition).where(ExamDefinition.family == family)
    if not include_draft:
        q = q.where(ExamDefinition.status == "active")
    result = await db.execute(q)
    exams = result.scalars().all()
    return [_exam_def_to_dict(e) for e in exams]


@router.get("/definitions/{slug}", tags=["exam"])
async def get_exam_definition(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Single exam definition by slug. Returns active OR draft (public info)."""
    exam = await db.get(ExamDefinition, slug)
    if not exam:
        raise HTTPException(404, f"Exam '{slug}' not found in registry")
    return _exam_def_to_dict(exam)


@router.get("/study-modules/{exam_slug}", tags=["exam"])
async def get_exam_study_modules(
    exam_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Return educational modules relevant to a Gulf exam slug.

    Queries Module.content->meta->exam_slugs for the given slug.
    Returns ordered list of modules with their lesson count.
    """
    import re
    if not re.match(r"^[a-z0-9_-]{2,20}$", exam_slug):
        raise HTTPException(400, "Invalid exam slug")

    from sqlalchemy import text as sa_text

    result = await db.execute(
        sa_text("""
            SELECT id, code, title, content
            FROM modules
            WHERE is_published = true
              AND content->'meta'->'exam_slugs' @> (:slug)::jsonb
            ORDER BY (content->'meta'->>'order_in_specialty')::int ASC NULLS LAST
        """),
        {"slug": f'["{exam_slug}"]'},
    )
    rows = result.mappings().all()

    out = []
    for row in rows:
        content = row["content"] or {}
        meta = content.get("meta", {})
        lessons = content.get("lessons", [])
        out.append({
            "id": str(row["id"]),
            "code": row["code"],
            "title": row["title"],
            "order": meta.get("order_in_specialty", 99),
            "level": meta.get("level", "intermediate"),
            "duration_hours": meta.get("duration_hours", 0),
            "lesson_count": len(lessons),
            "jurisdiction": meta.get("jurisdiction"),
            "blueprint_categories": meta.get("blueprint_categories", []),
        })

    return out


# ── V7 Phase 5: Community comparison ─────────────────────────────────────────

@router.get("/questions/{question_id}/community")
async def get_question_community_stats(
    question_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return community pass rate for a question.

    Only returned when sample_size_ok=True (min 40 attempts by default).
    Returns {available: false} otherwise — privacy guard.
    """
    try:
        qid = uuid_lib.UUID(question_id)
    except ValueError:
        raise HTTPException(404, "Question not found")

    stats = (await db.execute(
        select(QuestionStats).where(
            QuestionStats.question_id == qid,
            QuestionStats.exam_slug.is_(None),
        )
    )).scalar_one_or_none()

    if not stats or not stats.sample_size_ok or stats.p_value is None:
        return {"available": False}

    pct = round(stats.p_value * 100, 1)
    return {
        "available": True,
        "pass_rate_pct": pct,
        "attempts": stats.attempts,
    }


@router.get("/nclex/community-percentile")
async def get_nclex_community_percentile(
    exam_slug: str = Query("nclex"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return user's accuracy percentile per NCLEX category vs community.

    Minimum: 30 users in the group, 50 answers per user.
    Returns cached data computed nightly. {available: false} when data insufficient.
    """
    from app.core.cache import get_cached
    cache_key = f"community_pct:{exam_slug}:{user.id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    # Compute on demand (expensive — will be cached by nightly job)
    from app.core.config import settings as _cfg
    MIN_USER_ANSWERS = 50
    MIN_GROUP_SIZE = _cfg.PSYCHO_COMMUNITY_MIN_GROUP  # 30

    # Get user's category accuracy
    user_attempts = (await db.execute(
        select(QuestionAttempt).where(
            QuestionAttempt.user_id == user.id,
            QuestionAttempt.is_first_attempt == True,  # noqa: E712
            QuestionAttempt.session_type.in_(["practice", "exam", "mock"]),
        )
    )).scalars().all()

    if len(user_attempts) < MIN_USER_ANSWERS:
        return {"available": False, "reason": f"You need at least {MIN_USER_ANSWERS} answers to see your percentile."}

    # For each attempt, get question category
    qids = list({a.question_id for a in user_attempts})
    questions = (await db.execute(
        select(MCQQuestion.id, MCQQuestion.nclex_client_needs).where(MCQQuestion.id.in_(qids))
    )).all()
    q_category = {str(q.id): q.nclex_client_needs for q in questions}

    from collections import defaultdict
    user_cat: dict = defaultdict(lambda: {"correct": 0, "total": 0})
    for a in user_attempts:
        cat = q_category.get(str(a.question_id)) or "other"
        user_cat[cat]["total"] += 1
        if a.is_correct:
            user_cat[cat]["correct"] += 1

    return {
        "available": True,
        "categories": [
            {
                "category": cat,
                "accuracy_pct": round(v["correct"] / v["total"] * 100, 1) if v["total"] > 0 else None,
                "attempts": v["total"],
                "percentile": None,  # nightly job fills this
                "min_group_met": False,
            }
            for cat, v in user_cat.items() if v["total"] >= 5
        ],
        "note": "Percentile vs community updated nightly.",
    }


# ── V7 Phase 6: Mock Exam Debrief ────────────────────────────────────────────

@router.get("/sessions/{session_id}/mock-debrief")
async def get_mock_debrief(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Comprehensive debrief for completed mock sessions.

    Returns: score, timing analysis, pattern detectors, category delta,
    and practice session link for weak areas.
    """
    from app.services.mock_debrief import run_detectors, analyze_timing
    from app.models.models import ExamSession as _ExamSession

    sess = await db.get(_ExamSession, uuid_lib.UUID(session_id))
    if not sess or sess.user_id != user.id:
        raise HTTPException(404, "Session not found")
    if sess.status not in ("completed", "expired"):
        raise HTTPException(400, "Session not yet completed")

    per_q = sess.per_question or []
    snapshot = (sess.answers or {}).get("_snapshot", [])

    # Enrich per_q with question text for keyword detector
    q_text_map = {str(q.get("id")): q.get("question", "") for q in snapshot}
    for pq in per_q:
        pq["question_text"] = q_text_map.get(str(pq.get("question_id") or ""), "")

    patterns = run_detectors(per_q)
    timing = analyze_timing(per_q)

    # Category breakdown with delta to NCLEX pass threshold (62%)
    cat_breakdown = {}
    for pq in per_q:
        if pq.get("correct") is None:
            continue
        cat = pq.get("nclex_client_needs") or "other"
        if cat not in cat_breakdown:
            cat_breakdown[cat] = {"correct": 0, "total": 0}
        cat_breakdown[cat]["total"] += 1
        if pq["correct"]:
            cat_breakdown[cat]["correct"] += 1

    TARGET_PCT = 62
    cat_report = []
    for cat, v in cat_breakdown.items():
        accuracy = round(v["correct"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        cat_report.append({
            "category": cat,
            "accuracy_pct": accuracy,
            "total": v["total"],
            "delta_to_target": round(accuracy - TARGET_PCT, 1),
            "below_target": accuracy < TARGET_PCT,
        })
    cat_report.sort(key=lambda x: x["accuracy_pct"])

    weak_cats = [c["category"] for c in cat_report if c["below_target"]]

    # Mode info for pass threshold
    mode_data = next((m for m in EXAM_MODES if m["id"] == (sess.mode_id or "")), None)
    pass_threshold = mode_data["pass_threshold"] if mode_data else 62
    exam_slug = mode_data.get("exam_slug") if mode_data else None

    # Emit analytics event (best-effort)
    try:
        from app.core.cache import set_cached
        import datetime as _dt
        event_key = f"mock_completed:{session_id}"
        await set_cached(event_key, {
            "session_id": session_id,
            "user_id": str(user.id),
            "score_pct": sess.score_pct,
            "passed": sess.passed,
            "patterns_fired": [p["id"] for p in patterns],
            "at": _dt.datetime.utcnow().isoformat(),
        }, ttl=86400 * 7)
    except Exception:
        pass

    return {
        "session_id": session_id,
        "mode_id": sess.mode_id,
        "score_pct": sess.score_pct,
        "passed": sess.passed,
        "pass_threshold": pass_threshold,
        "total_questions": len(per_q),
        "correct": sess.correct,
        "wrong": sess.wrong,
        "timing": timing,
        "patterns": patterns,
        "category_breakdown": cat_report,
        "weak_categories": weak_cats,
        "train_weak_available": len(weak_cats) > 0,
        "exam_slug": exam_slug,
    }


@router.get("/sessions/{session_id}/mock-debrief/pdf")
async def download_mock_debrief_pdf(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download mock exam debrief as PDF."""
    from fastapi.responses import StreamingResponse
    from io import BytesIO
    from app.models.models import ExamSession as _ExamSession

    sess = await db.get(_ExamSession, uuid_lib.UUID(session_id))
    if not sess or sess.user_id != user.id:
        raise HTTPException(404, "Session not found")
    if sess.status not in ("completed", "expired"):
        raise HTTPException(400, "Session not yet completed")

    pdf_bytes = _generate_debrief_pdf(sess, user)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="mock-debrief-{session_id[:8]}.pdf"',
        },
    )


def _generate_debrief_pdf(sess: Any, user: Any) -> bytes:
    """Generate mock debrief PDF using reportlab."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    styles = {
        "title": ParagraphStyle("title", fontSize=20, fontName="Helvetica-Bold",
                                spaceAfter=6, textColor=colors.HexColor("#c0392b")),
        "subtitle": ParagraphStyle("subtitle", fontSize=12, fontName="Helvetica",
                                   spaceAfter=4, textColor=colors.HexColor("#4a453e")),
        "heading": ParagraphStyle("heading", fontSize=13, fontName="Helvetica-Bold",
                                  spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("body", fontSize=10, fontName="Helvetica",
                               spaceAfter=4, leading=14),
    }

    elements = []
    elements.append(Paragraph("MedMind AI", styles["title"]))
    elements.append(Paragraph(f"Mock Exam Debrief — {sess.mode_id or 'Exam'}", styles["subtitle"]))
    elements.append(Paragraph(
        f"Student: {user.first_name or ''} {user.last_name or ''}  |  Score: {sess.score_pct or 0:.1f}%  |  {'PASSED' if sess.passed else 'NOT PASSED'}",
        styles["body"]
    ))
    elements.append(Spacer(1, 8*mm))

    # Category breakdown table
    per_q = sess.per_question or []
    cat_breakdown: dict = {}
    for pq in per_q:
        if pq.get("correct") is None:
            continue
        cat = pq.get("nclex_client_needs") or "Other"
        if cat not in cat_breakdown:
            cat_breakdown[cat] = {"correct": 0, "total": 0}
        cat_breakdown[cat]["total"] += 1
        if pq["correct"]:
            cat_breakdown[cat]["correct"] += 1

    if cat_breakdown:
        elements.append(Paragraph("Category Performance", styles["heading"]))
        table_data = [["Category", "Score", "Status"]]
        for cat, v in sorted(cat_breakdown.items()):
            acc = v["correct"] / v["total"] * 100 if v["total"] > 0 else 0
            table_data.append([
                cat.replace("_", " ").title(),
                f"{acc:.1f}% ({v['correct']}/{v['total']})",
                "✓ Above target" if acc >= 62 else "⚠ Below target",
            ])
        tbl = Table(table_data, colWidths=[90*mm, 50*mm, 40*mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1814")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f7f4")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8d2c8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(tbl)
        elements.append(Spacer(1, 6*mm))

    elements.append(Paragraph(
        "Generated by MedMind AI · medmindai.com",
        ParagraphStyle("footer", fontSize=8, textColor=colors.HexColor("#8a8278"))
    ))

    doc.build(elements)
    return buf.getvalue()
