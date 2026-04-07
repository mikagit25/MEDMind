"""Pydantic schemas for MedMind AI API."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


# ============================================================
# AUTH SCHEMAS
# ============================================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "student"
    consent_terms: bool
    consent_data_processing: bool
    consent_marketing: bool = False

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("consent_terms", "consent_data_processing")
    def must_consent(cls, v):
        if not v:
            raise ValueError("Consent is required")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


# ============================================================
# USER SCHEMAS
# ============================================================
class UserOut(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    subscription_tier: str
    xp: int
    level: int
    streak_days: int
    onboarding_completed: bool
    preferences: Dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, **kwargs):
        instance = super().model_validate(obj, **kwargs)
        # Decrypt email if it was Fernet-encrypted in the DB
        try:
            from app.core.encryption import decrypt_email
            instance.email = decrypt_email(instance.email)
        except Exception:
            pass
        return instance


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    profile_data: Optional[Dict[str, Any]] = None


# ============================================================
# SPECIALTY SCHEMAS
# ============================================================
class SpecialtyOut(BaseModel):
    id: UUID
    code: str
    name: str
    name_en: Optional[str]
    icon: Optional[str]
    description: Optional[str]
    is_veterinary: bool
    module_count: int = 0

    model_config = {"from_attributes": True}


# ============================================================
# MODULE SCHEMAS
# ============================================================
class ModuleOut(BaseModel):
    id: UUID
    code: str
    title: str
    title_en: Optional[str]
    description: Optional[str]
    level: int
    level_label: Optional[str]
    module_order: int
    duration_hours: Optional[float]
    is_fundamental: bool
    is_published: bool
    specialty_id: Optional[UUID]
    lesson_count: int = 0
    flashcard_count: int = 0
    mcq_count: int = 0

    model_config = {"from_attributes": True}


class ModuleDetail(ModuleOut):
    content: Optional[Dict[str, Any]]
    prerequisite_codes: Optional[List[str]]


# ============================================================
# LESSON SCHEMAS
# ============================================================
class LessonOut(BaseModel):
    id: UUID
    module_id: UUID
    lesson_code: Optional[str]
    title: str
    lesson_order: int
    estimated_minutes: int

    model_config = {"from_attributes": True}


class LessonDetail(LessonOut):
    content: Dict[str, Any]


# ============================================================
# FLASHCARD SCHEMAS
# ============================================================
class FlashcardOut(BaseModel):
    id: UUID
    module_id: UUID
    question: str
    answer: str
    difficulty: str
    category: Optional[str]

    model_config = {"from_attributes": True}


class FlashcardReviewRequest(BaseModel):
    flashcard_id: UUID
    quality: int  # 0-5 per SM-2


class FlashcardReviewResponse(BaseModel):
    flashcard_id: UUID
    next_review_at: datetime
    interval_days: int
    ease_factor: float
    xp_earned: int


# ============================================================
# MCQ SCHEMAS
# ============================================================
class MCQQuestionOut(BaseModel):
    id: UUID
    module_id: UUID
    question: str
    options: Dict[str, str]
    difficulty: str

    model_config = {"from_attributes": True}


class MCQAnswerRequest(BaseModel):
    question_id: UUID
    selected_option: str  # "A", "B", "C", "D", "E"


class MCQAnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    explanation: str
    xp_earned: int


# ============================================================
# CLINICAL CASE SCHEMAS
# ============================================================
class ClinicalCaseOut(BaseModel):
    id: UUID
    module_id: UUID
    title: str
    specialty: Optional[str]
    presentation: str
    vitals: Optional[Dict[str, Any]]
    diagnosis: Optional[str]
    difficulty: str

    model_config = {"from_attributes": True}


class ClinicalCaseDetail(ClinicalCaseOut):
    differential_diagnosis: Optional[List[str]]
    management: Optional[List[str]]
    teaching_points: Optional[List[str]]


# ============================================================
# PROGRESS SCHEMAS
# ============================================================
class LessonCompleteRequest(BaseModel):
    lesson_id: UUID


class LessonCompleteResponse(BaseModel):
    xp_earned: int
    total_xp: int
    level: int
    module_completion_percent: float


class CaseCompleteRequest(BaseModel):
    answer: str


class CaseCompleteResponse(BaseModel):
    correct: bool
    explanation: str
    xp_gained: int


class ProgressStats(BaseModel):
    total_xp: int
    level: int
    streak_days: int
    lessons_completed: int
    flashcards_mastered: int
    mcq_accuracy: float
    modules_in_progress: int
    modules_completed: int
    modules_started: int = 0      # alias: modules with any activity
    cards_reviewed: int = 0
    mcqs_answered: int = 0
    correct_rate: float = 0.0
    total_sessions: int = 0


class ProgressHistoryItem(BaseModel):
    date: str
    xp_gained: int
    lessons: int
    cards: int


# ============================================================
# AI SCHEMAS
# ============================================================
class AIAskRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None
    specialty: str = "General Medicine"
    mode: str = "tutor"  # tutor|socratic|case|exam
    search_pubmed: bool = True


class AIAskResponse(BaseModel):
    reply: str
    conversation_id: UUID
    model_used: str
    from_cache: bool
    pubmed_refs: Optional[List[Dict[str, Any]]] = None
    xp_earned: int = 2


class ConversationOut(BaseModel):
    id: UUID
    title: Optional[str]
    specialty: Optional[str]
    mode: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    pubmed_refs: Optional[List[Dict[str, Any]]]
    from_cache: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# ONBOARDING
# ============================================================
class OnboardingData(BaseModel):
    role: str
    goal: str  # exam_prep|cme_credits|stay_updated|general_knowledge
    specialties: List[str]
    daily_minutes: int  # 10|20|30|45|60


# ============================================================
# DRUGS
# ============================================================
class DrugOut(BaseModel):
    id: UUID
    name: str
    generic_name: Optional[str] = None
    drug_class: Optional[str] = None
    mechanism: Optional[str] = None
    indications: Optional[List[str]] = None
    contraindications: Optional[List[str]] = None
    adverse_effects: Optional[Dict[str, Any]] = None
    dosing: Optional[Dict[str, Any]] = None
    is_high_yield: bool = False
    is_veterinary: bool = False

    model_config = {"from_attributes": True}
