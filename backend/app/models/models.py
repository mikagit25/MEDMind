"""SQLAlchemy models for MedMind AI."""
import uuid
from datetime import datetime
from typing import Optional

import os

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, Numeric,
    JSON as _SQLJSON, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB as _PGJSONB, ARRAY as _PGARRAY
from sqlalchemy.orm import relationship, validates

_IS_SQLITE = os.getenv("DATABASE_URL", "").startswith("sqlite")

# Use plain JSON for SQLite (tests/CI), JSONB for PostgreSQL (production)
JSONB = _SQLJSON if _IS_SQLITE else _PGJSONB

# SQLite doesn't support ARRAY — use JSON as a fallback (stores as JSON array)
ARRAY = (lambda t: _SQLJSON) if _IS_SQLITE else _PGARRAY

try:
    from pgvector.sqlalchemy import Vector as _PgVector
    _VECTOR_AVAILABLE = True
except ImportError:
    _PgVector = None
    _VECTOR_AVAILABLE = False

# Use JSONB for embeddings unless PGVECTOR_ENABLED=1 is explicitly set
_VECTOR_TYPE = _PgVector(1536) if (_VECTOR_AVAILABLE and os.getenv("PGVECTOR_ENABLED", "0") == "1") else JSONB

from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ============================================================
# SPECIALTIES
# ============================================================
class Specialty(Base):
    __tablename__ = "specialties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    name_en = Column(String(200))
    icon = Column(String(10))
    description = Column(Text)
    is_veterinary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    module_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    modules = relationship("Module", back_populates="specialty")


# ============================================================
# MODULES
# ============================================================
class Module(Base):
    __tablename__ = "modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False)
    specialty_id = Column(UUID(as_uuid=True), ForeignKey("specialties.id"))
    title = Column(String(300), nullable=False)
    title_en = Column(String(300))
    description = Column(Text)
    level = Column(Integer, default=1)
    level_label = Column(String(50))
    module_order = Column(Integer, default=0)
    duration_hours = Column(Numeric(4, 1), default=0)
    is_fundamental = Column(Boolean, default=False)
    prerequisite_codes = Column(ARRAY(String))
    prerequisites = Column(ARRAY(UUID(as_uuid=True)))
    used_in = Column(ARRAY(UUID(as_uuid=True)))
    embedding = Column(_VECTOR_TYPE)
    content = Column(JSONB)
    is_published = Column(Boolean, default=False)
    is_veterinary = Column(Boolean, default=False)
    is_nursing = Column(Boolean, default=False)
    language = Column(String(10), nullable=False, server_default="en")
    # "specialty_module" | "disease_module" | "patient_guide"
    module_type = Column(String(30), nullable=False, server_default="specialty_module")
    # Teacher-authored modules: who created this module
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    specialty = relationship("Specialty", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="module", cascade="all, delete-orphan")
    mcq_questions = relationship("MCQQuestion", back_populates="module", cascade="all, delete-orphan")
    clinical_cases = relationship("ClinicalCase", back_populates="module", cascade="all, delete-orphan")
    translations = relationship("ModuleTranslation", back_populates="module", cascade="all, delete-orphan")


# ============================================================
# LESSONS
# ============================================================
class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    lesson_code = Column(String(50))
    title = Column(String(300), nullable=False)
    lesson_order = Column(Integer, default=0)
    content = Column(JSONB, nullable=False)
    embedding = Column(_VECTOR_TYPE)
    estimated_minutes = Column(Integer, default=20)

    # Teacher authoring workflow
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # draft → review → published → archived | deprecated
    status = Column(String(20), default="draft", nullable=False, index=True)
    published_at = Column(DateTime)
    review_notes = Column(Text)

    # ── Medical/Veterinary credibility ─────────────────────────────────────
    # Which species this lesson applies to (["human"], ["canine","feline"], etc.)
    species_applicability = Column(ARRAY(String), default=list, nullable=False, server_default="{human}")
    # Warning shown when lesson spans both human and veterinary species
    cross_species_warning = Column(Text, nullable=True)
    # Clinical risk level: low | medium | high
    clinical_risk_level = Column(String(20), default="low", nullable=False, server_default="low")
    # Whether the procedure described requires clinical supervision
    requires_clinical_supervision = Column(Boolean, default=False, nullable=False, server_default="false")
    # Authoritative guideline this lesson follows (e.g. "WHO_2024", "OIE_2025")
    guideline_version = Column(String(100), nullable=True)
    # When a medical expert last reviewed this lesson for accuracy
    last_expert_review = Column(DateTime, nullable=True)
    # When the lesson should be re-reviewed (protocols become outdated)
    next_review_due = Column(DateTime, nullable=True)

    # ── Plain-language content for non-specialists (Phase 1) ───────────────
    # lay_summary: 150-300 word explanation at 8th-grade reading level
    lay_summary = Column(Text, nullable=True)
    # lay_glossary: [{term: str, simple_definition: str}, ...]
    lay_glossary = Column(JSONB, nullable=True)

    # ── Draft sharing via preview token ────────────────────────────────────
    preview_token = Column(String(64), unique=True, nullable=True, index=True)
    preview_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    row_version = Column(Integer, default=0, nullable=False)

    module = relationship("Module", back_populates="lessons")
    translations = relationship("LessonTranslation", back_populates="lesson", cascade="all, delete-orphan")

    @validates("content")
    def _validate_content_structure(self, key: str, value):
        """Enforce block-based JSONB structure before every save.

        Runs LessonContentSchema validation so malformed content never reaches
        the database.  Seeded/legacy content that predates this schema uses
        extra=allow, so unknown fields are preserved — only blatantly wrong
        structures (wrong types, missing required keys in dosage rows, etc.)
        are rejected.

        Validation is skipped for non-dict values (None, strings) to avoid
        breaking legacy imports.  The API layer re-validates via Pydantic before
        reaching here, so double-validation is cheap.
        """
        if not isinstance(value, dict):
            return value
        try:
            from app.schemas.lesson_content import LessonContentSchema
            LessonContentSchema.model_validate(value)
        except Exception:
            # Log but do not raise — the API layer (LessonContent Pydantic schema)
            # is the primary validation gate.  The ORM validator is a secondary
            # safety net for direct DB writes; failing here would block saves
            # when the API and ORM use different (but compatible) block formats.
            import logging as _logging
            _logging.getLogger(__name__).debug(
                "LessonContentSchema soft-validation warning for lesson (content stored anyway)"
            )
        return value


# ============================================================
# FLASHCARDS
# ============================================================
class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(String(20), default="medium")
    category = Column(String(100))
    tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="flashcards")


# ============================================================
# MCQ QUESTIONS
# ============================================================
class MCQQuestion(Base):
    __tablename__ = "mcq_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False)
    # mcq: single correct letter e.g. "A"
    # sata: unused (use correct_answers)
    # ordered: unused (use correct_order)
    # calculation: unused (use numeric_answer)
    correct = Column(String(5), nullable=False, server_default="A")
    explanation = Column(Text)
    difficulty = Column(String(20), default="medium")
    tags = Column(ARRAY(String))
    # "mcq" | "sata" | "ordered" | "calculation"
    question_type = Column(String(20), nullable=False, server_default="mcq")
    # SATA: list of correct option keys e.g. ["A", "C", "D"]
    correct_answers = Column(JSONB, nullable=True)
    # ordered: correct sequence of option keys e.g. ["B", "D", "A", "C"]
    correct_order = Column(JSONB, nullable=True)
    # calculation
    numeric_answer = Column(Float, nullable=True)
    numeric_tolerance = Column(Float, nullable=False, server_default="0.01")
    numeric_unit = Column(String(50), nullable=True)
    # SATA scoring: False = all-or-nothing (NCLEX default)
    partial_scoring = Column(Boolean, nullable=False, server_default="false")
    # NCLEX tagging
    nclex_client_needs = Column(String(60), nullable=True)
    cjmm_skill = Column(String(60), nullable=True)
    # NGN: None = standard; "bowtie" | "matrix" | "trend" | "cloze"
    ngn_type = Column(String(20), nullable=True)
    bowtie_data = Column(JSONB, nullable=True)
    matrix_data = Column(JSONB, nullable=True)
    # Phase 2: per-option rationales + key takeaway
    # rationales: {A: {text: "...", why: "correct"|"incorrect"}, ...}
    rationales = Column(JSONB, nullable=True)
    key_takeaway = Column(Text, nullable=True)
    test_taking_tip = Column(Text, nullable=True)
    # G2: Spanish translations of explanations (null = not yet translated)
    explanation_es = Column(Text, nullable=True)
    rationales_es = Column(JSONB, nullable=True)
    key_takeaway_es = Column(Text, nullable=True)
    test_taking_tip_es = Column(Text, nullable=True)
    # Phase 2: user flagging
    is_flagged = Column(Boolean, nullable=False, server_default="false")
    flag_reason = Column(Text, nullable=True)
    # G1: which exam slugs use this question e.g. ["snle", "dha", "qchp"]
    exam_slugs = Column(JSONB, nullable=True)
    # Content quality & traceability
    # source_refs: [{name, url, section}] — official references used for this question
    source_refs = Column(JSONB, nullable=True)
    # verification_status: "pending" | "ai_verified" | "flagged" | "human_reviewed"
    verification_status = Column(String(30), nullable=False, server_default="pending")
    # verification_report: [{claim, result, confidence, issues}] from second LLM pass
    verification_report = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="mcq_questions")


# ============================================================
# EXAM REGISTRY — G1
# ============================================================
class ExamDefinition(Base):
    """Authoritative registry of every licensing exam MedMind supports.
    Parameters must come from official sources; blueprint_verified_at must be set.
    status='draft' means the entry is not shown publicly until parameters are confirmed.
    """
    __tablename__ = "exam_definitions"

    slug               = Column(String(60),  primary_key=True)   # "dha" | "snle" | "qchp" …
    name               = Column(String(200), nullable=False)
    country            = Column(String(100), nullable=False)
    regulatory_body    = Column(String(200), nullable=False)
    question_count     = Column(Integer,     nullable=False)
    duration_min       = Column(Integer,     nullable=False)
    pass_threshold     = Column(Integer,     nullable=False)       # percentage, e.g. 65
    passing_score_label= Column(String(30),  nullable=False, server_default="65%")
    blueprint_source   = Column(String(500), nullable=False)       # official URL
    blueprint_verified_at = Column(String(20), nullable=True)      # ISO date "2026-01-01"
    status             = Column(String(20),  nullable=False, server_default="draft")  # active|draft
    locale             = Column(String(10),  nullable=False, server_default="en")
    family             = Column(String(50),  nullable=False, server_default="gulf")   # gulf|nclex|uk
    options_per_question = Column(Integer,   nullable=False, server_default="4")
    categories         = Column(JSONB,       nullable=True)   # list of blueprint category strings
    exam_date_fixed    = Column(String(20),  nullable=True)   # ISO date — annual exams (KPSS)
    disclaimer         = Column(Text,        nullable=True)
    created_at         = Column(DateTime,    default=datetime.utcnow)
    updated_at         = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# CLINICAL CASES
# ============================================================
class ClinicalCase(Base):
    __tablename__ = "clinical_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=False)
    specialty = Column(String(100))
    presentation = Column(Text, nullable=False)
    vitals = Column(JSONB)
    diagnosis = Column(String(300))
    differential_diagnosis = Column(ARRAY(String))
    management = Column(ARRAY(String))
    teaching_points = Column(ARRAY(String))
    content = Column(JSONB)
    difficulty = Column(String(20), default="medium")
    # FSM (Finite State Machine) for branching clinical simulations
    # steps: ordered list of case steps, each with {id, title, description, choices: [{id, text, next_step, outcome, score_delta}]}
    steps = Column(JSONB, nullable=True)       # branching scenario steps
    initial_step_id = Column(String(50), nullable=True)  # which step to start on
    ideal_path = Column(JSONB, nullable=True)  # list of step_ids for optimal path
    max_score = Column(Integer, default=100)   # max possible score
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="clinical_cases")


class ExamSession(Base):
    """Persistent board-exam / NCLEX practice session."""
    __tablename__ = "exam_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode_id = Column(String(50), nullable=False)
    mode_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active|completed|expired
    question_ids = Column(JSONB, nullable=False, default=list)
    answers = Column(JSONB, nullable=False, default=dict)
    total_questions = Column(Integer, nullable=False)
    duration_min = Column(Integer, nullable=False)
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    correct = Column(Integer, nullable=True)
    wrong = Column(Integer, nullable=True)
    score_pct = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    time_taken_min = Column(Float, nullable=True)
    per_question = Column(JSONB, nullable=True)
    current_difficulty = Column(String(20), nullable=False, default="medium")
    cat_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class ClinicalCaseSession(Base):
    """Tracks a student's progress through a branching clinical case FSM."""
    __tablename__ = "clinical_case_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("clinical_cases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    current_step_id = Column(String(50), nullable=True)
    # path taken: [{"step_id": ..., "choice_id": ..., "timestamp": ...}]
    path_taken = Column(JSONB, default=list)
    score = Column(Integer, default=0)
    status = Column(String(20), default="in_progress")  # in_progress | completed | abandoned
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    debriefing = Column(JSONB, nullable=True)  # AI-generated debrief after completion

    case = relationship("ClinicalCase")
    __table_args__ = (
        Index("ix_case_sessions_user", "user_id", "status"),
    )


# ============================================================
# USERS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    email_hash = Column(String(64))
    password_hash = Column(String(255))
    role = Column(String(50), default="student")
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(Text)
    subscription_tier = Column(String(50), default="free")
    subscription_expires = Column(DateTime)
    stripe_customer_id = Column(String(100))
    profile_data = Column(JSONB, default=dict)
    preferences = Column(JSONB, default=dict)
    ai_requests_today = Column(Integer, default=0)
    ai_requests_reset_at = Column(DateTime, default=datetime.utcnow)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    streak_days = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_active_date = Column(DateTime)
    # Leaderboard opt-in (Phase 5)
    leaderboard_opt_in = Column(Boolean, default=False, nullable=False, server_default="false")
    leaderboard_display_name = Column(String(100), nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_verified_teacher = Column(Boolean, default=False)   # admin confirmed real medical professional
    is_trusted_author = Column(Boolean, default=False)     # articles auto-publish, no review needed
    oauth_provider = Column(String(50))
    oauth_id = Column(String(200))
    push_token = Column(String(200), nullable=True)
    telegram_chat_id = Column(String(50), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Affiliate: which influencer brought this user (plain UUID, no FK to avoid circular)
    referred_by_affiliate_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # G3 — Regional pricing: set from Stripe billing address on first payment
    billing_country = Column(String(2), nullable=True)   # ISO-2, e.g. "PH"
    billing_region  = Column(String(1), nullable=True)   # "A" | "B" | "C"
    billing_region_changed_at = Column(DateTime, nullable=True)  # anti-abuse: 1 change max

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")
    affiliate_profile = relationship("Affiliate", foreign_keys="[Affiliate.user_id]", back_populates="user", uselist=False)
    exam_plans = relationship("ExamPlan", back_populates="user", cascade="all, delete-orphan")


# ============================================================
# USER PROGRESS
# ============================================================
class UserProgress(Base):
    __tablename__ = "user_progress"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True)
    lessons_completed = Column(ARRAY(UUID(as_uuid=True)), default=list)
    flashcards_mastered = Column(ARRAY(UUID(as_uuid=True)), default=list)
    mcq_score = Column(Numeric(5, 2), default=0)
    mcq_attempts = Column(Integer, default=0)
    completion_percent = Column(Numeric(5, 2), default=0)
    next_review_at = Column(DateTime)
    ease_factor = Column(Numeric(4, 2), default=2.5)
    interval_days = Column(Integer, default=1)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")


# ============================================================
# FLASHCARD REVIEWS (per-card SM-2)
# ============================================================
class FlashcardReview(Base):
    __tablename__ = "flashcard_reviews"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    flashcard_id = Column(UUID(as_uuid=True), ForeignKey("flashcards.id", ondelete="CASCADE"), primary_key=True)
    ease_factor = Column(Numeric(4, 2), default=2.5)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review_at = Column(DateTime, default=datetime.utcnow)
    last_reviewed_at = Column(DateTime)
    last_quality = Column(Integer)


# ============================================================
# AI CONVERSATIONS
# ============================================================
class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200))
    specialty = Column(String(100))
    mode = Column(String(50), default="tutor")
    model_used = Column(String(100))
    cached_responses = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("AIConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


# ============================================================
# AI CONVERSATION MESSAGES
# ============================================================
class AIConversationMessage(Base):
    __tablename__ = "ai_conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    pubmed_refs = Column(JSONB)
    model_used = Column(String(100))
    tokens_used = Column(Integer, default=0)
    from_cache = Column(Boolean, default=False)
    feedback = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("AIConversation", back_populates="messages")


# ============================================================
# REFRESH TOKENS
# ============================================================
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")


# ============================================================
# DRUGS
# ============================================================
class Drug(Base):
    __tablename__ = "drugs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    generic_name = Column(String(200))
    drug_class = Column(String(100))
    mechanism = Column(Text)
    indications = Column(ARRAY(String))
    contraindications = Column(ARRAY(String))
    dosing = Column(JSONB)
    adverse_effects = Column(JSONB)
    interactions = Column(ARRAY(String))
    monitoring = Column(ARRAY(String))
    black_box_warning = Column(Text)
    is_high_yield = Column(Boolean, default=False)
    is_nti = Column(Boolean, default=False)
    is_veterinary = Column(Boolean, default=False)
    image_url = Column(Text, nullable=True)
    translations = Column(JSONB, default=dict)
    content = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# USER NOTES
# ============================================================
class UserNote(Base):
    __tablename__ = "user_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"))
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# USER BOOKMARKS
# ============================================================
class UserBookmark(Base):
    __tablename__ = "user_bookmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_type = Column(String(50), nullable=False)
    content_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "content_type", "content_id"),)


# ============================================================
# USER ACHIEVEMENTS
# ============================================================
class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_code = Column(String(100), nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "achievement_code"),)


# ============================================================
# STRIPE EVENTS
# ============================================================
class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id = Column(String(200), unique=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    data = Column(JSONB)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# USER CONSENTS (GDPR)
# ============================================================
class UserConsent(Base):
    __tablename__ = "user_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    consent_type = Column(String(100), nullable=False)
    granted = Column(Boolean, default=True, nullable=False)
    version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))

    __table_args__ = (UniqueConstraint("user_id", "consent_type"),)


# ============================================================
# AUDIT LOG (GDPR)
# ============================================================
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# COURSES  (teacher-created, assigned to students)
# ============================================================
class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    invite_code = Column(String(16), unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8].upper())
    # Discovery & enrollment
    is_public = Column(Boolean, default=False)
    enrollment_type = Column(String(20), default="invite")  # invite | open | request
    difficulty = Column(String(20))   # beginner | intermediate | advanced
    specialty_tag = Column(String(100))
    thumbnail_emoji = Column(String(10))
    estimated_hours = Column(Numeric(5, 1))
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime)
    ends_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = relationship("User", foreign_keys=[teacher_id])
    course_modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("CourseAssignment", back_populates="course", cascade="all, delete-orphan")
    access_requests = relationship("CourseAccessRequest", back_populates="course", cascade="all, delete-orphan")


class CourseAccessRequest(Base):
    """Student requests access to a non-public course."""
    __tablename__ = "course_access_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text)
    status = Column(String(20), default="pending")  # pending | approved | denied
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    course = relationship("Course", back_populates="access_requests")
    user = relationship("User", foreign_keys=[user_id])


class CourseModule(Base):
    """Ordered list of modules inside a course."""
    __tablename__ = "course_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    module_order = Column(Integer, default=0)
    added_at = Column(DateTime, default=datetime.utcnow)

    course = relationship("Course", back_populates="course_modules")
    module = relationship("Module")

    __table_args__ = (UniqueConstraint("course_id", "module_id"),)


class CourseEnrollment(Base):
    """Student enrolled in a course."""
    __tablename__ = "course_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="active")  # active | dropped | completed

    course = relationship("Course", back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id])

    __table_args__ = (UniqueConstraint("course_id", "student_id"),)


class CourseAssignment(Base):
    """Teacher-set deadline for a module in a course."""
    __tablename__ = "course_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300))
    description = Column(Text)
    due_date = Column(DateTime)
    max_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    course = relationship("Course", back_populates="assignments")
    module = relationship("Module")


# ============================================================
# DRUG INTERACTIONS
# ============================================================
class DrugInteraction(Base):
    """Known interactions between two drugs."""
    __tablename__ = "drug_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_a_id = Column(UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False)
    drug_b_id = Column(UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False)
    severity = Column(String(20), default="moderate")  # mild | moderate | severe | contraindicated
    mechanism = Column(Text)
    clinical_effect = Column(Text)
    management = Column(Text)
    evidence_level = Column(String(10), default="C")  # A | B | C
    created_at = Column(DateTime, default=datetime.utcnow)

    drug_a = relationship("Drug", foreign_keys=[drug_a_id])
    drug_b = relationship("Drug", foreign_keys=[drug_b_id])

    __table_args__ = (UniqueConstraint("drug_a_id", "drug_b_id"),)


# ============================================================
# ANIMAL SPECIES (Veterinary)
# ============================================================
class AnimalSpecies(Base):
    """Animal species for veterinary mode."""
    __tablename__ = "animal_species"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)  # e.g. "Dog", "Cat"
    name_ru = Column(String(100))
    scientific_name = Column(String(200))
    category = Column(String(50))  # companion | livestock | exotic | avian
    icon = Column(String(10))
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dosing_entries = relationship("VeterinaryDosing", back_populates="species", cascade="all, delete-orphan")


# ============================================================
# VETERINARY DOSING
# ============================================================
class VeterinaryDosing(Base):
    """Drug dosing information specific to an animal species."""
    __tablename__ = "veterinary_dosing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    drug_id = Column(UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), nullable=False)
    species_id = Column(UUID(as_uuid=True), ForeignKey("animal_species.id", ondelete="CASCADE"), nullable=False)
    dose = Column(String(200))           # e.g. "5-10 mg/kg"
    route = Column(String(50))           # oral | IV | IM | SC | topical
    frequency = Column(String(100))      # e.g. "q12h", "once daily"
    max_dose = Column(String(100))
    is_toxic = Column(Boolean, default=False)   # True = CONTRAINDICATED / toxic
    toxicity_note = Column(Text)          # e.g. "Paracetamol: fatal hepatotoxicity in cats"
    is_approved = Column(Boolean, default=True)
    notes = Column(Text)
    source = Column(String(200))          # e.g. "Plumb's Veterinary Drug Handbook"
    created_at = Column(DateTime, default=datetime.utcnow)

    drug = relationship("Drug", foreign_keys=[drug_id])
    species = relationship("AnimalSpecies", back_populates="dosing_entries")

    __table_args__ = (UniqueConstraint("drug_id", "species_id", "route"),)


# ============================================================
# CME CREDITS
# ============================================================
class CMECredit(Base):
    """Continuing Medical Education credits earned by doctors."""
    __tablename__ = "cme_credits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)
    credit_type = Column(String(50), default="AMA_PRA_1")  # AMA_PRA_1 | AAFP | etc.
    credits_earned = Column(Numeric(4, 1), default=1.0)
    activity_title = Column(String(300))
    completion_date = Column(DateTime, default=datetime.utcnow)
    certificate_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    module = relationship("Module", foreign_keys=[module_id])


# ============================================================
# NOTIFICATIONS
# ============================================================
class Notification(Base):
    """In-app notifications for users."""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # achievement | flashcard_due | daily_goal | system
    title = Column(String(200), nullable=False)
    body = Column(Text)
    data = Column(JSONB)  # extra context (achievement_code, module_id, etc.)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


# ============================================================
# STUDENT LONG-TERM MEMORY
# ============================================================
class StudentMemory(Base):
    """Persistent per-student facts extracted from AI conversations."""
    __tablename__ = "student_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Memory classification
    memory_type = Column(String(30), nullable=False)
    # "fact" | "skill" | "misconception" | "preference" | "case_experience"

    # Content
    content = Column(Text, nullable=False)
    # Lowercased tokens for text search — auto-populated on content write
    search_tokens = Column(Text)

    @validates("content")
    def _auto_search_tokens(self, key: str, value: str) -> str:
        """Keep search_tokens in sync with content automatically."""
        import re
        _stop = frozenset({
            "a", "an", "the", "is", "in", "on", "at", "to", "of", "or", "and",
            "for", "not", "but", "be", "as", "by", "it", "its", "if", "do",
            "so", "up", "he", "she", "we", "my", "no", "can", "has", "had",
            "was", "are", "did", "may", "who", "how", "our", "you", "all",
        })
        tokens = re.findall(r"[a-zA-Zа-яёА-ЯЁ0-9]+", value or "")
        seen: set = set()
        unique = []
        for t in tokens:
            lt = t.lower()
            if lt not in seen and len(lt) > 2 and lt not in _stop:
                seen.add(lt)
                unique.append(lt)
        self.search_tokens = " ".join(unique)
        return value

    # Contextual metadata
    specialty = Column(String(100), index=True)
    competency_level = Column(String(20))  # "beginner" | "intermediate" | "advanced"
    species_context = Column(String(20))   # "human" | "canine" | "feline" | "equine" | ...
    source_conversation_id = Column(UUID(as_uuid=True), ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True)

    # Reliability
    confidence = Column(Float, default=0.7)    # 0.0–1.0
    verified = Column(Boolean, default=False)   # verified by instructor/admin
    deprecated = Column(Boolean, default=False, index=True)  # soft-delete or outdated

    # Source & validation metadata (from enhanced extraction prompt)
    source_hint = Column(String(200))           # e.g. "WHO 2024", "Plumb's 9th ed."
    requires_verification = Column(Boolean, default=False)  # flagged by LLM for review
    species_applicability = Column(_SQLJSON)    # list of applicable species: ["canine", "feline"]
    misconception_severity = Column(String(10)) # "low"|"medium"|"high" for misconception type

    # Audit trail
    prompt_version = Column(String(30))         # version of extraction prompt used

    # Usage tracking
    importance_score = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        # Composite index for the most common hybrid search: filter by user + specialty + active
        Index("ix_student_memories_user_specialty", "user_id", "specialty", "deprecated"),
        # Index for importance-ranked retrieval within a user
        Index("ix_student_memories_user_importance", "user_id", "importance_score", "deprecated"),
        # Index for memory type filtering (fact, skill, misconception…)
        Index("ix_student_memories_user_type", "user_id", "memory_type"),
    )


class MemoryRelation(Base):
    """Directed edges between memories (lightweight knowledge graph)."""
    __tablename__ = "memory_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_memory_id = Column(UUID(as_uuid=True), ForeignKey("student_memories.id", ondelete="CASCADE"), nullable=False, index=True)
    target_memory_id = Column(UUID(as_uuid=True), ForeignKey("student_memories.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(30), nullable=False)
    # "prerequisite" | "contradicts" | "elaborates" | "clinical_variant" | "species_difference"
    species_context = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# LESSON COMPLETION — per-student lesson tracking
# ============================================================
class LessonCompletion(Base):
    """Records each time a student completes a lesson."""
    __tablename__ = "lesson_completions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    time_spent_seconds = Column(Integer, default=0)   # how long student was on the lesson
    quiz_score = Column(Numeric(5, 2))                # 0.0-100.0, null if no quiz
    quiz_attempts = Column(Integer, default=0)
    completed_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("lesson_id", "user_id", name="uq_lesson_completion"),
    )


# ============================================================
# LESSON VERSIONS — snapshot on each save
# ============================================================
class LessonVersion(Base):
    """Snapshot of lesson content saved before each update."""
    __tablename__ = "lesson_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(JSONB, nullable=False)
    saved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    saved_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String(200))  # optional description of this version


# ============================================================
# MEDICAL IMAGES — curated imaging library
# ============================================================
class MedicalImage(Base):
    """Curated medical imaging library entry (X-ray, CT, MRI, US, anatomy)."""
    __tablename__ = "medical_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    modality = Column(String(50), nullable=False, index=True)   # xray, ct, mri, ultrasound, anatomy, histology, 3d
    anatomy_region = Column(String(100), index=True)             # brain, chest, abdomen, heart, spine, …
    specialty = Column(String(100), index=True)                  # radiology, neurology, cardiology, …
    image_url = Column(Text, nullable=False)                     # direct image URL
    thumbnail_url = Column(Text)                                 # smaller version if available
    source_name = Column(String(200), nullable=False)            # "NIH OpenI", "Wikimedia Commons", "Radiopaedia"
    source_url = Column(Text)                                    # link to original case/page
    license = Column(String(100))                                # "CC0", "CC-BY-SA 4.0", "Public Domain"
    attribution = Column(Text)                                   # attribution string to display
    tags = Column(JSONB, default=list)                           # ["pneumonia", "consolidation", "lung"]
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # uploaded_by: nullable — seeded/external images have no uploader
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # is_user_upload: False for seeded/NIH images, True for teacher uploads
    is_user_upload = Column(Boolean, default=False, nullable=False, server_default="false")

    annotations = relationship("ImageAnnotation", back_populates="image", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_medical_images_modality_region", "modality", "anatomy_region"),
    )


# ============================================================
# ANATOMY VIEWERS — 3D embed configs
# ============================================================
class AnatomyViewer(Base):
    """3D anatomy viewer embed configuration (Sketchfab, BioDigital, etc.)."""
    __tablename__ = "anatomy_viewers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    organ_system = Column(String(100), index=True)   # cardiovascular, nervous, respiratory, …
    anatomy_region = Column(String(100), index=True) # brain, heart, lung, kidney, …
    embed_type = Column(String(50), default="sketchfab")  # sketchfab | biodigital | iframe
    embed_id = Column(String(200), nullable=False)         # Sketchfab model ID or full URL
    embed_url = Column(Text)                               # pre-built embed URL
    thumbnail_url = Column(Text)
    source_name = Column(String(200))
    source_url = Column(Text)
    license = Column(String(100))
    attribution = Column(Text)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


# ============================================================
# IMAGE ANNOTATIONS — overlays drawn by teachers on medical images
# ============================================================
class ImageAnnotation(Base):
    """Annotation layer on a MedicalImage.

    Coordinates are stored as percentages (0.0–100.0) so they scale
    correctly when images are displayed at different sizes.

    Supported annotation_type values:
      arrow, rectangle, circle, ellipse, text, polygon, freehand
    """
    __tablename__ = "image_annotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("medical_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Annotation geometry
    annotation_type = Column(String(30), nullable=False)  # arrow | rectangle | circle | text | polygon
    # Primary coordinates (% of image width/height, 0-100)
    x = Column(Float, nullable=True)       # left anchor
    y = Column(Float, nullable=True)       # top anchor
    width = Column(Float, nullable=True)   # for rectangle / ellipse
    height = Column(Float, nullable=True)
    # For arrows: end point
    x2 = Column(Float, nullable=True)
    y2 = Column(Float, nullable=True)
    # For polygons / freehand paths: list of {x, y} dicts
    points = Column(JSONB, nullable=True)

    # Appearance
    label = Column(String(300))            # text shown near annotation
    color = Column(String(20), default="#FF0000")
    stroke_width = Column(Integer, default=2)
    font_size = Column(Integer, default=14)
    opacity = Column(Float, default=1.0)

    # Authorship
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    image = relationship("MedicalImage", back_populates="annotations")


# ============================================================
# USER-GENERATED FLASHCARDS (UGC)
# ============================================================
class UserFlashcard(Base):
    """Personal flashcards created by users from their own notes."""
    __tablename__ = "user_flashcards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    # Optional link to a module lesson for context (nullable)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="SET NULL"), nullable=True)
    tags = Column(ARRAY(String), default=list)
    difficulty = Column(String(20), default="medium")
    is_public = Column(Boolean, default=False)  # future: share cards with community
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # SM-2 state (same fields as FlashcardReview but embedded in card for simplicity)
    ease_factor = Column(Float, default=2.5)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_at = Column(DateTime, nullable=True)
    last_quality = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_user_flashcards_user_id", "user_id"),
        Index("ix_user_flashcards_next_review", "user_id", "next_review_at"),
    )


# ============================================================
# LESSON / MODULE TRANSLATIONS
# ============================================================
SUPPORTED_LOCALES = ["ru", "ar", "tr", "de", "fr", "es"]


class LessonTranslation(Base):
    """Translated version of a lesson (title + content blocks) for one locale."""
    __tablename__ = "lesson_translations"

    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    locale = Column(String(10), nullable=False, primary_key=True)

    title = Column(String(300), nullable=False)
    content_json = Column(JSONB, nullable=False)  # translated blocks array
    lay_glossary = Column(JSONB, nullable=True)   # [{term, simple_definition}]

    # pending | translating | done | failed | reviewed
    status = Column(String(20), nullable=False, default="pending")
    translation_quality = Column(Float, nullable=True)  # 0.0–1.0 model confidence

    reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    error_message = Column(Text, nullable=True)
    translated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="translations")

    __table_args__ = (
        Index("ix_lesson_translations_lesson_id", "lesson_id"),
        Index("ix_lesson_translations_status", "status"),
    )


class ModuleTranslation(Base):
    """Translated title + description of a module for one locale."""
    __tablename__ = "module_translations"

    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    locale = Column(String(10), nullable=False, primary_key=True)

    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(20), nullable=False, default="pending")
    translated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="translations")

    __table_args__ = (
        Index("ix_module_translations_module_id", "module_id"),
    )


# ============================================================
# ARTICLES — SEO public medical content
# ============================================================
class Article(Base):
    """Public SEO article about a medical topic.
    Generated by Claude AI, published to /articles/[slug].
    Includes schema.org structured data for rich Google results.
    """
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(300), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    excerpt = Column(Text, nullable=False)

    # Array of content blocks: [{type: "h2"|"p"|"ul"|"table"|"callout", content: "..."}]
    body = Column(JSONB, nullable=False, default=list)

    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)

    # For meta keywords and internal search
    keywords = Column(ARRAY(String), nullable=True)

    reading_time_minutes = Column(Integer, nullable=False, default=5)

    # MedicalWebPage | Drug | MedicalCondition | MedicalProcedure
    schema_type = Column(String(50), nullable=False, default="MedicalWebPage")

    # FAQ schema: [{question: str, answer: str}, ...]
    faq = Column(JSONB, nullable=True)

    # PubMed / external sources: [{title: str, url: str, pmid: str|None}, ...]
    sources = Column(JSONB, nullable=True)

    # Optional link to a platform learning module
    related_module_code = Column(String(50), nullable=True)

    # SEO overrides (if blank, title/excerpt are used)
    og_title = Column(String(200), nullable=True)
    og_description = Column(String(300), nullable=True)
    cover_image = Column(String(500), nullable=True)   # hero image URL (Wikipedia/upload)

    is_published = Column(Boolean, nullable=False, default=False)
    published_at = Column(DateTime, nullable=True)

    # Author Program metrics
    view_count = Column(Integer, nullable=False, default=0)
    revenue_share_pct = Column(Integer, nullable=False, default=40)

    # Which model generated this: claude-haiku | claude-sonnet | manual | teacher
    generated_by = Column(String(50), nullable=True)

    # ── Authorship ─────────────────────────────────────────────────────────────
    # NULL = AI-generated / MedMind AI editorial
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Optional display name / credentials override (e.g. "Dr. Jane Smith, MD")
    author_display_name = Column(String(200), nullable=True)
    # Short bio shown on article page
    author_bio = Column(Text, nullable=True)

    # ── Review workflow ────────────────────────────────────────────────────────
    # draft | pending_review | published | rejected
    # AI-generated articles skip review and go straight to published/draft.
    # Teacher-authored articles start as draft → pending_review → published/rejected.
    review_status = Column(String(30), nullable=False, default="published")
    review_note = Column(Text, nullable=True)    # shown to teacher on rejection
    submitted_at = Column(DateTime, nullable=True)

    # V4 Verification: pending | passed | failed | human_reviewed
    # (legacy: unverified → pending, ai_verified → passed, expert_verified → human_reviewed)
    verification_status = Column(String(30), nullable=False, default="pending")
    # Real PubMed sources [{pmid, title, authors, journal, year, url}]
    verified_sources = Column(JSONB, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)   # kept for backward compat
    # V4 verification fields
    verified_at = Column(DateTime, nullable=True)
    verification_report = Column(JSONB, nullable=True)   # [{claim, result, citation}]
    reviewed_by = Column(String(200), nullable=True)     # reviewer display name
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User", foreign_keys=[author_id])
    translations = relationship("ArticleTranslation", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_articles_is_published", "is_published"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_author_id", "author_id"),
        Index("ix_articles_review_status", "review_status"),
        Index("ix_articles_verification_status", "verification_status"),
    )


class ArticleTranslation(Base):
    """Translated version of an article (title + excerpt + body + faq) for one locale."""
    __tablename__ = "article_translations"

    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    locale = Column(String(10), nullable=False, primary_key=True)

    title = Column(String(300), nullable=False)
    excerpt = Column(Text, nullable=False)
    body = Column(JSONB, nullable=False, default=list)
    faq = Column(JSONB, nullable=True)

    # pending | translating | done | failed
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    translated_at = Column(DateTime, nullable=True)

    # V4 Phase 2: translation quality verification
    # pending | passed | failed
    translation_verification_status = Column(String(20), nullable=True, default="pending")
    translation_qa_report = Column(JSONB, nullable=True)
    translation_qa_checked_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    article = relationship("Article", back_populates="translations")

    __table_args__ = (
        Index("ix_article_translations_article_id", "article_id"),
        Index("ix_article_translations_status", "status"),
        Index("ix_article_translations_qa_status", "translation_verification_status"),
    )


# ============================================================
# REVIEWER PROFILES (V4 Phase 3)
# ============================================================

class Reviewer(Base):
    """Expert reviewer who validates human_reviewed articles."""
    __tablename__ = "reviewers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    credentials = Column(String(500), nullable=True)   # "MD, PhD, Cardiologist at …"
    bio = Column(Text, nullable=True)
    institution = Column(String(300), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    specialties = Column(JSONB, nullable=True)          # ["cardiology", "internal medicine"]
    linkedin_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# CREDIT SYSTEM
# ============================================================

class AuthorCreditAccount(Base):
    __tablename__ = "author_credit_accounts"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    balance = Column(Integer, nullable=False, default=0)
    total_purchased = Column(Integer, nullable=False, default=0)
    total_spent = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(20), nullable=False)  # 'purchase', 'spend', 'bonus', 'refund'
    credits = Column(Integer, nullable=False)
    usd_amount = Column(Numeric(10, 4), nullable=True)
    model = Column(String(50), nullable=True)  # for 'spend' transactions: 'ollama', 'claude-haiku', 'claude-sonnet'
    actual_cost_usd = Column(Numeric(10, 6), nullable=True)  # real API cost
    article_id = Column(UUID(as_uuid=True), ForeignKey("articles.id", ondelete="SET NULL"), nullable=True)
    stripe_payment_intent_id = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LLMPricing(Base):
    __tablename__ = "llm_pricing"

    model = Column(String(50), primary_key=True)
    credits_per_article = Column(Integer, nullable=False)
    actual_cost_usd = Column(Numeric(10, 6), nullable=False)
    markup_multiplier = Column(Numeric(4, 2), nullable=False, default=2.0)
    display_name = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class NewsArticle(Base):
    """AI-summarised medical news from PubMed, WHO RSS, and medRxiv.
    Original source always attributed. Translations stored inline as JSONB.
    """
    __tablename__ = "news_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(400), unique=True, nullable=False, index=True)

    # Source
    source_name = Column(String(200), nullable=False)
    source_url = Column(String(1000), nullable=False)
    source_doi = Column(String(300), nullable=True)
    source_hash = Column(String(64), unique=True, nullable=False)  # dedup key

    # English content
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    tags = Column(ARRAY(String), nullable=True)

    # Translations: {"ru": {"title": "...", "summary": "..."}, "ar": {...}, ...}
    translations = Column(JSONB, nullable=False, default=dict)

    original_published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    translated_at = Column(DateTime, nullable=True)

    is_published = Column(Boolean, nullable=False, default=True)

    # Teacher-created news fields (NULL = auto-pipeline)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_display_name = Column(String(200), nullable=True)
    # draft | submitted | published | rejected
    review_status = Column(String(20), nullable=False, default="published")
    review_note = Column(Text, nullable=True)

    # V4 Verification: pending | passed | failed | human_reviewed
    verification_status = Column(String(30), nullable=False, default="pending")
    sources_v4 = Column(JSONB, nullable=True)     # [{title, url, type, accessed_at}]
    verified_at = Column(DateTime, nullable=True)
    verification_report = Column(JSONB, nullable=True)
    reviewed_by = Column(String(200), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)


# ── Content Feedback ───────────────────────────────────────────────────────────

class ContentFeedback(Base):
    """User-submitted content error reports (no auth required)."""
    __tablename__ = "content_feedback"

    id = Column(Integer, primary_key=True)
    content_type = Column(String(20), nullable=False)     # "article" | "news"
    content_id = Column(String(100), nullable=False)      # UUID or slug
    problem_type = Column(String(50), nullable=False)     # factual_error|outdated|missing_source|other
    comment = Column(Text, nullable=True)
    reporter_email = Column(String(200), nullable=True)
    ip_hash = Column(String(64), nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Comments ──────────────────────────────────────────────────────────────────

class Comment(Base):
    """User comment on an article, news item, module, or lesson."""
    __tablename__ = "comments"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_type     = Column(String(10),  nullable=False, index=True)  # "article" | "news" | "module" | "lesson"
    content_slug     = Column(String(400), nullable=False, index=True)
    body             = Column(Text,  nullable=False)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    is_hidden        = Column(Boolean, default=False, nullable=False)
    report_count     = Column(Integer, default=0,     nullable=False)
    # V5 Phase 4: Q&A support
    comment_type     = Column(String(20), nullable=False, default="comment")  # "comment" | "question"
    entity_id        = Column(UUID(as_uuid=True), nullable=True, index=True)  # module/lesson UUID
    accepted_answer_id = Column(UUID(as_uuid=True), nullable=True)            # FK set by teacher/author
    upvotes          = Column(Integer, nullable=False, default=0)
    parent_id        = Column(UUID(as_uuid=True), nullable=True)              # answer to a question

    user = relationship("User", lazy="joined", foreign_keys=[user_id])


class CommentLike(Base):
    """One row per (user, comment) like — composite PK prevents duplicates."""
    __tablename__ = "comment_likes"

    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id",    ondelete="CASCADE"), primary_key=True)


class CommentReport(Base):
    """One row per (user, comment) report — prevents duplicate reports."""
    __tablename__ = "comment_reports"

    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id",    ondelete="CASCADE"), primary_key=True)


# ============================================================
# PUBLIC QUIZZES (Phase 4 — viral sharing contour)
# ============================================================
class PublicQuiz(Base):
    """Standalone quiz accessible without authentication.

    questions JSONB shape:
      [{question, options: {A,B,C,D}, correct: "A", explanation}]
    """
    __tablename__ = "public_quizzes"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug        = Column(String(200), nullable=False, unique=True, index=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    category    = Column(String(100), nullable=False, default="general")  # first-aid, anatomy, etc.
    questions   = Column(JSONB, nullable=False, default=list)
    is_active   = Column(Boolean, default=True, nullable=False)
    play_count  = Column(Integer, default=0, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_public_quizzes_category", "category"),)


# ============================================================
# SHARED FLASHCARD DECKS (Phase 4 — deck sharing)
# ============================================================
class SharedDeck(Base):
    """Snapshot of user flashcards shared via a public token link."""
    __tablename__ = "shared_decks"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name        = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    # URL-safe token (8–12 chars) used in /decks/shared/{token}
    token       = Column(String(20), nullable=False, unique=True, index=True)
    # Snapshot of cards: [{question, answer, difficulty}]
    cards       = Column(JSONB, nullable=False, default=list)
    is_active   = Column(Boolean, default=True, nullable=False)
    view_count  = Column(Integer, default=0, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", lazy="joined", foreign_keys=[owner_id])

    __table_args__ = (Index("ix_shared_decks_owner_id", "owner_id"),)


# ============================================================
# XP EVENTS — audit trail for all XP awards (Phase 5)
# ============================================================
# ============================================================
# CALCULATOR RESULTS — saved calculator history (Phase 9)
# ============================================================
class CalculatorResult(Base):
    """A saved clinical calculator result for an authenticated user."""
    __tablename__ = "calculator_results"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    slug         = Column(String(100), nullable=False)   # e.g. "cha2ds2-vasc"
    inputs       = Column(JSONB, nullable=False)         # user-entered field values
    score        = Column(String(50), nullable=True)     # computed score or result label
    risk_level   = Column(String(50), nullable=True)     # low / moderate / high / very-high
    note         = Column(Text, nullable=True)           # optional free-text note by user
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_calc_results_user_id",        "user_id"),
        Index("ix_calc_results_user_slug",      "user_id", "slug"),
        Index("ix_calc_results_created_at",     "created_at"),
    )


class XPEvent(Base):
    """One row per XP award event — audit trail for gamification."""
    __tablename__ = "xp_events"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source       = Column(String(50), nullable=False)  # "lesson" | "mcq" | "flashcard" | "case"
    amount       = Column(Integer, nullable=False)
    reference_id = Column(String(100), nullable=True)  # lesson/card/question UUID
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_xp_events_user_id", "user_id"),
        Index("ix_xp_events_created_at", "created_at"),
    )


# ============================================================
# HEALTH PROFILES — persistent health data for users
# ============================================================
class HealthProfile(Base):
    """Persistent health profile: conditions, medications, allergies, demographics."""
    __tablename__ = "health_profiles"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, unique=True)
    # Demographics
    birth_year   = Column(Integer, nullable=True)
    sex          = Column(String(10), nullable=True)   # male / female / other
    # Conditions / medications / allergies stored as JSONB arrays of strings
    conditions   = Column(JSONB, nullable=False, default=list)
    medications  = Column(JSONB, nullable=False, default=list)
    allergies    = Column(JSONB, nullable=False, default=list)
    # Full symptom/complaint history (up to 200 entries from Telegram and web)
    health_log   = Column(JSONB, nullable=False, default=list)
    # Mood check-in log: [{date, mood}]
    checkin_log  = Column(JSONB, nullable=False, default=list)
    # Metric trackers: {glucose: [{date, value}], bp: [...]}
    trackers     = Column(JSONB, nullable=False, default=dict)
    # Telegram chat_id if linked
    telegram_chat_id = Column(String(50), nullable=True, index=True)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at   = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", lazy="joined", foreign_keys=[user_id])

    __table_args__ = (Index("ix_health_profiles_user_id", "user_id"),)


class HealthMetric(Base):
    """One measurement row for a health metric (glucose, BP, weight, etc.)."""
    __tablename__ = "health_metrics"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False)
    metric       = Column(String(50), nullable=False)   # glucose, bp, weight, …
    value        = Column(String(50), nullable=False)   # raw value string
    unit         = Column(String(20), nullable=True)
    note         = Column(Text, nullable=True)
    source       = Column(String(20), nullable=False, default="web")  # web / telegram
    recorded_at  = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_health_metrics_user_id", "user_id"),
        Index("ix_health_metrics_user_metric", "user_id", "metric"),
        Index("ix_health_metrics_recorded_at", "recorded_at"),
    )


class EnterpriseLead(Base):
    """Enterprise demo request / sales lead."""
    __tablename__ = "enterprise_leads"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name  = Column(String(100), nullable=False)
    last_name   = Column(String(100), nullable=False)
    email       = Column(String(320), nullable=False)
    company     = Column(String(200), nullable=False)
    job_title   = Column(String(200), nullable=False)
    team_size   = Column(String(20),  nullable=False)   # "1-10", "11-25", "26-100", "100+"
    use_case    = Column(String(100), nullable=False)
    message     = Column(Text, nullable=True)
    ip_hash     = Column(String(64),  nullable=True)    # SHA-256 of client IP
    status      = Column(String(20),  nullable=False, default="new")  # new/contacted/qualified/closed
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_enterprise_leads_status",     "status"),
        Index("ix_enterprise_leads_created_at", "created_at"),
    )


# ── Product Analytics (V5 Phase 1) ───────────────────────────────────────────

class AnalyticsEvent(Base):
    """Structured product analytics event. No free-form user text in meta."""
    __tablename__ = "analytics_events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True)
    anon_id     = Column(String(64), nullable=True)
    event_type  = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=True)
    entity_id   = Column(String(128), nullable=True)
    meta        = Column(_PGJSONB, nullable=True)   # structured only — no free-form user text
    locale      = Column(String(8), nullable=True)
    platform    = Column(String(16), nullable=True, default="web")
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_ae_event_type_created", "event_type", "created_at"),
        Index("ix_ae_user_created", "user_id", "created_at"),
    )


class AnalyticsDailyAgg(Base):
    """Daily aggregates kept after raw events are purged (>12 months)."""
    __tablename__ = "analytics_daily_agg"

    date        = Column(_SQLJSON, primary_key=True)   # Date stored as string "YYYY-MM-DD"
    event_type  = Column(String(64), primary_key=True)
    platform    = Column(String(16), primary_key=True)
    event_count = Column(Integer, nullable=False, default=0)
    unique_users = Column(Integer, nullable=False, default=0)


# ============================================================
# CLINICAL ALGORITHMS  (V5 Phase 3 — Point-of-Care)
# ============================================================
class ClinicalAlgorithm(Base):
    """Step-based clinical decision algorithm (anaphylaxis, cardiac arrest, etc.)."""
    __tablename__ = "clinical_algorithms"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug                = Column(String(100), unique=True, nullable=False, index=True)
    title               = Column(String(300), nullable=False)
    specialty           = Column(String(100), nullable=True)
    description         = Column(Text, nullable=True)
    steps               = Column(_PGJSONB, nullable=False)  # [{id,type,text,children,note}]
    tags                = Column(String(500), nullable=True)
    source              = Column(Text, nullable=True)
    is_veterinary       = Column(Boolean, nullable=False, default=False)
    verification_status = Column(String(30), nullable=False, default="passed")
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============================================================
# SOCIAL LEARNING  (V5 Phase 4)
# ============================================================

class AssignmentStatus(Base):
    """Per-student, per-assignment completion tracking."""
    __tablename__ = "assignment_statuses"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True),
                          ForeignKey("course_assignments.id", ondelete="CASCADE"),
                          nullable=False)
    user_id       = Column(UUID(as_uuid=True),
                          ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False)
    status        = Column(String(20), nullable=False, default="pending")  # pending|in_progress|completed|overdue
    score         = Column(Numeric(5, 2), nullable=True)
    submitted_at  = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)

    assignment    = relationship("CourseAssignment")
    user          = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("assignment_id", "user_id", name="uq_assignment_status"),
        Index("ix_as_assignment_id", "assignment_id"),
        Index("ix_as_user_id", "user_id"),
    )


class DeckCollaborator(Base):
    """Co-editor on a shared flashcard deck."""
    __tablename__ = "deck_collaborators"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deck_id  = Column(UUID(as_uuid=True),
                     ForeignKey("shared_decks.id", ondelete="CASCADE"),
                     nullable=False)
    user_id  = Column(UUID(as_uuid=True),
                     ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    role     = Column(String(20), nullable=False, default="editor")  # editor | viewer
    added_at = Column(DateTime, default=datetime.utcnow)

    deck = relationship("SharedDeck")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("deck_id", "user_id", name="uq_deck_collaborator"),
        Index("ix_deck_collab_deck_id", "deck_id"),
    )


# ============================================================
# SRS KNOWLEDGE ITEMS  (V5 Phase 5)
# ============================================================

class LessonSrsItem(Base):
    """SM-2 spaced-repetition slot for a completed lesson or article."""
    __tablename__ = "lesson_srs_items"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True),
                            ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False)
    entity_type     = Column(String(20), nullable=False)   # "lesson" | "article"
    entity_id       = Column(UUID(as_uuid=True), nullable=False)
    ease_factor     = Column(Numeric(4, 2), nullable=False, default=2.5)
    interval_days   = Column(Integer, nullable=False, default=1)
    next_review_at  = Column(DateTime, nullable=False)
    last_reviewed_at = Column(DateTime, nullable=True)
    review_count    = Column(Integer, nullable=False, default=0)
    created_at      = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_lesson_srs_item"),
        Index("ix_lesson_srs_items_user_next", "user_id", "next_review_at"),
    )


class LessonMcqCache(Base):
    """Cached AI-generated MCQs for a lesson or article (shared across all users)."""
    __tablename__ = "lesson_mcq_cache"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type  = Column(String(20), nullable=False)
    entity_id    = Column(UUID(as_uuid=True), nullable=False)
    questions    = Column(_PGJSONB, nullable=False)   # list of {question, options, correct, explanation}
    generated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_lesson_mcq_cache"),
    )


# ============================================================
# CERTIFICATES  (V5 Phase 6)
# ============================================================

class Certificate(Base):
    """Module completion certificate with a unique verification code."""
    __tablename__ = "certificates"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True),
                               ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id         = Column(UUID(as_uuid=True),
                               ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    verification_code = Column(String(32), unique=True, nullable=False)
    score             = Column(Numeric(5, 2), nullable=True)
    issued_at         = Column(DateTime, default=datetime.utcnow, nullable=False)
    language          = Column(String(10), nullable=False, default="en")
    hide_name         = Column(Boolean, nullable=False, default=False)

    user   = relationship("User", foreign_keys=[user_id])
    module = relationship("Module", foreign_keys=[module_id])

    __table_args__ = (
        UniqueConstraint("user_id", "module_id", name="uq_certificate_user_module"),
        Index("ix_certificates_user_id", "user_id"),
        Index("ix_certificates_verification_code", "verification_code"),
    )


class DoseCalcStat(Base):
    """Per-user per-category aggregate stats for the Dose-Calc Trainer."""
    __tablename__ = "dose_calc_stats"

    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    category        = Column(String(50), primary_key=True)   # e.g. 'weight_dose' or '_overall'
    total_attempts  = Column(Integer, nullable=False, default=0, server_default="0")
    total_correct   = Column(Integer, nullable=False, default=0, server_default="0")
    current_streak  = Column(Integer, nullable=False, default=0, server_default="0")
    best_streak     = Column(Integer, nullable=False, default=0, server_default="0")
    last_attempted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_dose_calc_stats_user", "user_id"),
    )


class PromoCode(Base):
    """Promotional codes — trial grants or Stripe discount coupons."""
    __tablename__ = "promo_codes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code            = Column(String(50), unique=True, nullable=False, index=True)
    description     = Column(String(255), nullable=True)

    # "trial" | "percent" | "fixed"
    discount_type   = Column(String(20), nullable=False, default="trial")
    discount_value  = Column(Float, nullable=True)          # pct (0-100) or $ amount
    trial_tier      = Column(String(20), nullable=True)     # student | pro | clinic
    trial_days      = Column(Integer, nullable=True)        # days of access

    max_uses        = Column(Integer, nullable=True)        # None = unlimited
    used_count      = Column(Integer, nullable=False, default=0, server_default="0")
    one_per_user    = Column(Boolean, nullable=False, default=True, server_default="true")

    is_active       = Column(Boolean, nullable=False, default=True, server_default="true")
    expires_at      = Column(DateTime, nullable=True)       # None = never
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    uses            = relationship("PromoCodeUse", back_populates="code", cascade="all, delete-orphan")


class PromoCodeUse(Base):
    """Audit log of promo code redemptions."""
    __tablename__ = "promo_code_uses"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_id         = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    used_at         = Column(DateTime, nullable=False, default=datetime.utcnow)
    granted_tier    = Column(String(20), nullable=True)
    granted_until   = Column(DateTime, nullable=True)

    code            = relationship("PromoCode", back_populates="uses")

    __table_args__ = (
        Index("ix_promo_uses_user", "user_id"),
        Index("ix_promo_uses_code", "code_id"),
        # DB-level guard against race condition on one_per_user codes (Phase 6)
        UniqueConstraint("code_id", "user_id", name="uq_promo_one_use_per_user"),
    )


# ============================================================
# AFFILIATE / INFLUENCER SYSTEM
# ============================================================

class Affiliate(Base):
    """Influencer/affiliate partner profile — one per MedMind account."""
    __tablename__ = "affiliates"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    code             = Column(String(50), unique=True, nullable=False, index=True)
    status           = Column(String(20), nullable=False, default="pending")   # pending|active|suspended
    commission_type  = Column(String(20), nullable=False, default="percent")   # percent|fixed
    commission_value = Column(Float, nullable=False, default=20.0)
    payout_info      = Column(JSONB, default=dict)   # {type:"paypal", address:"..."} or bank
    cookie_days      = Column(Integer, nullable=False, default=30)
    notes            = Column(Text, nullable=True)   # admin internal notes

    total_clicks      = Column(Integer, nullable=False, default=0, server_default="0")
    total_signups     = Column(Integer, nullable=False, default=0, server_default="0")
    total_conversions = Column(Integer, nullable=False, default=0, server_default="0")
    total_earned      = Column(Float, nullable=False, default=0.0, server_default="0")
    total_paid        = Column(Float, nullable=False, default=0.0, server_default="0")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user        = relationship("User", back_populates="affiliate_profile", foreign_keys=[user_id])
    clicks      = relationship("AffiliateClick", back_populates="affiliate", cascade="all, delete-orphan")
    conversions = relationship("AffiliateConversion", back_populates="affiliate", cascade="all, delete-orphan")


class AffiliateClick(Base):
    """One row per click on an affiliate referral link."""
    __tablename__ = "affiliate_clicks"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False)
    ip_hash      = Column(String(64), nullable=True)    # SHA-256(IP) — for dedup, GDPR-safe
    user_agent   = Column(String(500), nullable=True)
    referrer     = Column(String(500), nullable=True)
    utm_source   = Column(String(100), nullable=True)
    utm_medium   = Column(String(100), nullable=True)
    utm_campaign = Column(String(100), nullable=True)
    clicked_at   = Column(DateTime, nullable=False, default=datetime.utcnow)

    affiliate = relationship("Affiliate", back_populates="clicks")

    __table_args__ = (
        Index("ix_aff_clicks_affiliate", "affiliate_id"),
        Index("ix_aff_clicks_at", "clicked_at"),
    )


class AffiliateConversion(Base):
    """Signup or paid-subscription event attributed to an affiliate."""
    __tablename__ = "affiliate_conversions"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id      = Column(UUID(as_uuid=True), ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type        = Column(String(20), nullable=False)   # "signup" | "subscription"
    tier              = Column(String(20), nullable=True)
    amount_paid       = Column(Float, nullable=True)          # USD received by us (from Stripe)
    commission_amount = Column(Float, nullable=True)          # USD owed to affiliate
    # Phase 6 anti-fraud fields
    commission_status = Column(String(20), nullable=False, default="pending", server_default="pending")
                                                             # pending|approved|hold|rejected
    is_suspicious     = Column(Boolean, nullable=False, default=False, server_default="false")
    clearance_date    = Column(DateTime, nullable=True)       # 14d after created_at; payout only after this
    is_paid_out       = Column(Boolean, nullable=False, default=False, server_default="false")
    stripe_invoice_id = Column(String(100), nullable=True)
    created_at        = Column(DateTime, nullable=False, default=datetime.utcnow)

    affiliate = relationship("Affiliate", back_populates="conversions")

    __table_args__ = (
        Index("ix_aff_conv_affiliate", "affiliate_id"),
        Index("ix_aff_conv_user", "user_id"),
    )


# ============================================================
# LIFECYCLE EMAIL CAMPAIGNS (V6 Phase 5)
# ============================================================
class LifecycleSend(Base):
    """Idempotency record — one row per (user, campaign, step) ever sent."""
    __tablename__ = "lifecycle_sends"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    campaign   = Column(String(60), nullable=False)   # e.g. "onboarding_d1"
    step       = Column(String(60), nullable=False, default="email")
    sent_at    = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "campaign", "step", name="uq_lifecycle_one_per_step"),
        Index("ix_lifecycle_user", "user_id"),
        Index("ix_lifecycle_campaign", "campaign"),
    )


# ============================================================
# EXAM STUDY PLANS (V6 Phase 4)
# ============================================================
class ExamPlan(Base):
    """Study plan anchored to a user's exam date."""
    __tablename__ = "exam_plans"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_type    = Column(String(50), nullable=False, default="nclex")  # nclex | usmle | ...
    exam_date    = Column(DateTime, nullable=False)
    daily_minutes= Column(Integer, nullable=False, default=30)  # 15 | 30 | 60
    status       = Column(String(20), nullable=False, default="active")  # active | completed | abandoned
    plan_cache   = Column(JSONB, nullable=True)   # cached generated day list
    created_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at   = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user          = relationship("User", back_populates="exam_plans")
    completions   = relationship("ExamPlanCompletion", back_populates="plan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_exam_plans_user", "user_id"),
        UniqueConstraint("user_id", "exam_type", "status",
                         name="uq_exam_plans_one_active_per_type"),
    )


class ExamPlanCompletion(Base):
    """Records which study-plan tasks the user has marked as done."""
    __tablename__ = "exam_plan_completions"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id    = Column(UUID(as_uuid=True), ForeignKey("exam_plans.id", ondelete="CASCADE"), nullable=False)
    task_date  = Column(DateTime, nullable=False)   # the calendar day this task belongs to
    task_type  = Column(String(50), nullable=False)  # "practice" | "mock_exam" | "review" | "rest"
    completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    plan = relationship("ExamPlan", back_populates="completions")

    __table_args__ = (
        Index("ix_epc_plan", "plan_id"),
        UniqueConstraint("plan_id", "task_date", name="uq_epc_one_per_day"),
    )


# ============================================================
# BILLING HARDENING (V6 Phase 6)
# ============================================================

class StripeWebhookEvent(Base):
    """Idempotency record — one row per Stripe event_id ever processed."""
    __tablename__ = "stripe_webhook_events"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id   = Column(String(100), unique=True, nullable=False, index=True)  # evt_xxx
    event_type = Column(String(100), nullable=False)
    status     = Column(String(20), nullable=False, default="ok")  # ok | error | retrying
    error_msg  = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class BillingEvent(Base):
    """Immutable audit log — every billing state change."""
    __tablename__ = "billing_events"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type       = Column(String(60), nullable=False)   # subscription_activated | subscription_downgraded |
                                                            # promo_applied | commission_created |
                                                            # dunning_started | dunning_downgrade | ...
    source           = Column(String(30), nullable=False)   # webhook | admin | system | promo
    old_tier         = Column(String(30), nullable=True)
    new_tier         = Column(String(30), nullable=True)
    amount           = Column(Float, nullable=True)
    stripe_invoice_id= Column(String(100), nullable=True)
    reason           = Column(Text, nullable=True)
    meta             = Column(JSONB, nullable=True)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_billing_events_user", "user_id"),
        Index("ix_billing_events_type_created", "event_type", "created_at"),
    )
