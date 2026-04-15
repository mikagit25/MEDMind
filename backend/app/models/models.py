"""SQLAlchemy models for MedMind AI."""
import uuid
from datetime import datetime
from typing import Optional

import os

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, Numeric,
    JSON as _SQLJSON,
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
    # Teacher-authored modules: who created this module
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    specialty = relationship("Specialty", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="module", cascade="all, delete-orphan")
    mcq_questions = relationship("MCQQuestion", back_populates="module", cascade="all, delete-orphan")
    clinical_cases = relationship("ClinicalCase", back_populates="module", cascade="all, delete-orphan")


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
    # draft → review → published → archived
    status = Column(String(20), default="published", nullable=False, index=True)
    published_at = Column(DateTime)
    review_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    row_version = Column(Integer, default=0, nullable=False)

    module = relationship("Module", back_populates="lessons")


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
    correct = Column(String(5), nullable=False)
    explanation = Column(Text)
    difficulty = Column(String(20), default="medium")
    tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="mcq_questions")


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
    created_at = Column(DateTime, default=datetime.utcnow)

    module = relationship("Module", back_populates="clinical_cases")


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
    last_active_date = Column(DateTime)
    onboarding_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    oauth_provider = Column(String(50))
    oauth_id = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    progress = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("AIConversation", back_populates="user", cascade="all, delete-orphan")


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
    # invite code — students join with this
    invite_code = Column(String(16), unique=True, nullable=False, default=lambda: uuid.uuid4().hex[:8].upper())
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime)
    ends_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    teacher = relationship("User", foreign_keys=[teacher_id])
    course_modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    assignments = relationship("CourseAssignment", back_populates="course", cascade="all, delete-orphan")


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
    tags = Column(_PGARRAY(String), default=list)
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
