"""Typed Pydantic schemas for lesson content blocks.

The lesson `content` column is JSONB and accepts any JSON.  These schemas
enforce a consistent block-based structure so:
  - the frontend renderer can rely on predictable field shapes
  - dosage tables always include species/dose/route
  - image blocks always carry alt_text (accessibility)
  - the publication validator can reason about block types

Usage (validation before save):
    from app.schemas.lesson_content import LessonContentSchema
    validated = LessonContentSchema(**raw_dict)
    lesson.content = validated.model_dump()

Usage (discriminated union for one block):
    from app.schemas.lesson_content import parse_block
    block = parse_block({"type": "text", "order": 0, "content": "..."})
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Valid species / risk level constants (mirrored in lessons.py route)
# ─────────────────────────────────────────────────────────────────────────────
VALID_SPECIES = frozenset({
    "human", "canine", "feline", "equine", "bovine",
    "porcine", "ovine", "avian", "exotic",
})

VALID_RISK_LEVELS = frozenset({"low", "medium", "high"})


# ─────────────────────────────────────────────────────────────────────────────
# Shared mixin for all blocks
# ─────────────────────────────────────────────────────────────────────────────
class _BaseBlock(BaseModel):
    """Common fields present on every content block."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    order: int = Field(ge=0)
    required: bool = True  # If False, student may skip this block
    # Adaptive display: evaluated by the frontend, ignored by the backend
    show_if: Optional[Dict[str, Any]] = None  # e.g. {"user_level": "intermediate+"}
    hide_if: Optional[Dict[str, Any]] = None  # e.g. {"species_context": "feline"}
    # Inline clinical warning (shown prominently in the UI)
    clinical_warning: Optional[str] = None
    evidence_level: Optional[str] = None  # "A" | "B" | "C" | "D" — evidence quality for the clinical claim in this block
    guideline_reference: Optional[str] = None  # e.g. "AHA 2023 Heart Failure Guidelines, Class I Rec."

    model_config = {"extra": "allow"}


# ─────────────────────────────────────────────────────────────────────────────
# Concrete block types
# ─────────────────────────────────────────────────────────────────────────────
class TextBlock(_BaseBlock):
    """Rich Markdown body.  Minimum 10 characters to prevent empty blocks."""
    type: Literal["text"] = "text"
    content: str = Field(..., min_length=10, description="Markdown-formatted text")
    learning_objective: Optional[str] = None
    # Optional list of risk tags: ["clinical_risk", "species_specific", "off_label"]
    warnings: Optional[List[str]] = None


class ImageBlock(_BaseBlock):
    """Medical image block — either from MedicalImage library or an external URL."""
    type: Literal["image"] = "image"
    # Exactly one of image_id or url must be supplied
    image_id: Optional[str] = None        # FK into medical_images table (UUID as string)
    url: Optional[str] = None             # External URL
    alt_text: str = Field(..., min_length=5, description="Screen-reader description (required)")
    caption: Optional[str] = None
    source_attribution: Optional[str] = None   # e.g. "NIH OpenI, CC0"
    species_context: Optional[List[str]] = None

    @model_validator(mode="after")
    def require_source(self) -> "ImageBlock":
        if not self.image_id and not self.url:
            raise ValueError("ImageBlock requires either 'image_id' or 'url'")
        return self


class VideoBlock(_BaseBlock):
    """Embedded video (YouTube, Vimeo, or internal CDN)."""
    type: Literal["video"] = "video"
    url: str = Field(..., description="Video URL or embed URL")
    caption: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=None, ge=1)


class QuizBlock(_BaseBlock):
    """Multiple-choice question with immediate feedback."""
    type: Literal["quiz"] = "quiz"
    question: str = Field(..., min_length=10)
    options: Dict[str, str] = Field(
        ...,
        description="Keys A-E, values are option text",
    )
    correct: str = Field(..., description="Correct option key, e.g. 'B'")
    explanation: str = Field(..., min_length=10, description="Why the answer is correct")
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @field_validator("options")
    @classmethod
    def require_min_options(cls, v: Dict[str, str]) -> Dict[str, str]:
        if len(v) < 2:
            raise ValueError("Quiz must have at least 2 options")
        return v

    @field_validator("correct")
    @classmethod
    def correct_must_be_in_options(cls, v: str, info) -> str:
        opts = (info.data or {}).get("options", {})
        if opts and v not in opts:
            raise ValueError(f"'correct' key '{v}' is not in the options dict")
        return v


class ClinicalCaseBlock(_BaseBlock):
    """Embedded clinical case vignette."""
    type: Literal["clinical_case"] = "clinical_case"
    presentation: str = Field(..., min_length=20)
    diagnosis: Optional[str] = None
    management: Optional[List[str]] = None
    teaching_points: Optional[List[str]] = None
    species: str = Field(default="human", description="Patient species for vet cases")


class DosageTableBlock(_BaseBlock):
    """Species-specific dosing table — critical for pharmacology lessons.

    ``rows`` is a list of dicts with the shape:
        {species, dose, unit, route, frequency, warning?}
    """
    type: Literal["dosage_table"] = "dosage_table"
    drug_id: Optional[str] = None          # FK to drugs table (UUID as string)
    drug_name: Optional[str] = None        # Display name when no drug_id
    rows: List[Dict[str, Any]] = Field(..., min_length=1)
    requires_species_selection: bool = True  # Student must select species before viewing
    clinical_warning: Optional[str] = None  # Override base field for stronger typing here
    unit: str = "mg/kg"                    # Default dosing unit

    @field_validator("rows")
    @classmethod
    def rows_have_required_keys(cls, v: List[Dict]) -> List[Dict]:
        required_keys = {"species", "dose", "route"}
        for i, row in enumerate(v):
            missing = required_keys - set(row.keys())
            if missing:
                raise ValueError(f"Dosage row {i} is missing required keys: {missing}")
        return v


class Anatomy3DBlock(_BaseBlock):
    """3D anatomy viewer embed (Sketchfab, BioDigital, etc.)."""
    type: Literal["anatomy_3d"] = "anatomy_3d"
    viewer_id: Optional[str] = None        # FK to anatomy_viewers table
    embed_url: Optional[str] = None        # Direct embed URL
    caption: Optional[str] = None
    organ_system: Optional[str] = None    # e.g. "cardiovascular"


class FlashcardBlock(_BaseBlock):
    """Inline flashcard for spaced repetition within a lesson."""
    type: Literal["flashcard"] = "flashcard"
    question: str = Field(..., min_length=5)
    answer: str = Field(..., min_length=5)
    difficulty: Literal["easy", "medium", "hard"] = "medium"


# ─────────────────────────────────────────────────────────────────────────────
# Discriminated union — all block types
# ─────────────────────────────────────────────────────────────────────────────
AnyBlock = Annotated[
    Union[
        TextBlock,
        ImageBlock,
        VideoBlock,
        QuizBlock,
        ClinicalCaseBlock,
        DosageTableBlock,
        Anatomy3DBlock,
        FlashcardBlock,
    ],
    Field(discriminator="type"),
]


def parse_block(data: Dict[str, Any]) -> AnyBlock:
    """Parse a single block dict into the appropriate typed model."""
    from pydantic import TypeAdapter
    adapter: TypeAdapter[AnyBlock] = TypeAdapter(AnyBlock)
    return adapter.validate_python(data)


# ─────────────────────────────────────────────────────────────────────────────
# Guideline source
# ─────────────────────────────────────────────────────────────────────────────
class GuidelineSource(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    year: Optional[int] = Field(default=None, ge=2000, le=2035)
    url: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Top-level lesson content schema
# ─────────────────────────────────────────────────────────────────────────────
class LessonContentSchema(BaseModel):
    """Full validated structure for the `content` JSONB column of `Lesson`.

    Used by:
    - The `@validates("content")` event on the Lesson ORM model
    - The publication validator (lesson_validator.py)
    - The API layer (LessonContent in lessons.py route)

    Example::

        {
          "title": "Диагностика мастита у КРС",
          "blocks": [
            {"type": "text", "order": 0, "content": "## Этиология\\n..."},
            {"type": "dosage_table", "order": 1, "drug_name": "Амоксициллин",
             "rows": [{"species": "bovine", "dose": "15", "route": "IM"}]}
          ],
          "estimated_minutes": 20,
          "learning_objectives": ["Распознать клинические признаки мастита"],
          "species_applicability": ["bovine"],
          "clinical_risk_level": "medium",
          "guideline_sources": [{"name": "Merck Veterinary Manual", "year": 2025}]
        }
    """
    title: str = Field(..., min_length=2, max_length=300)
    blocks: List[AnyBlock] = Field(default_factory=list)
    estimated_minutes: int = Field(default=20, ge=5, le=180)
    learning_objectives: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="List of learning objectives (up to 10)",
    )

    # Medical / veterinary metadata
    species_applicability: List[str] = Field(default_factory=lambda: ["human"])
    clinical_risk_level: str = Field(default="low")
    guideline_sources: List[GuidelineSource] = Field(default_factory=list)
    cross_species_comparative: bool = Field(
        default=False,
        description="Set True when lesson intentionally covers multiple species side-by-side",
    )

    model_config = {"extra": "allow"}

    @field_validator("species_applicability")
    @classmethod
    def validate_species(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_SPECIES
        if invalid:
            raise ValueError(
                f"Unknown species: {sorted(invalid)}. "
                f"Valid values: {sorted(VALID_SPECIES)}"
            )
        return v

    @field_validator("clinical_risk_level")
    @classmethod
    def validate_risk(cls, v: str) -> str:
        if v not in VALID_RISK_LEVELS:
            raise ValueError(
                f"clinical_risk_level must be one of {sorted(VALID_RISK_LEVELS)}"
            )
        return v
