"""
Pydantic schemas for Prompt Classifier Engine.

Defines request/response models for prompt classification.
"""

from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class IntentType(str, Enum):
    """User intent classification."""
    INFORMATIONAL = "informational"
    EVALUATION = "evaluation"
    DECISION = "decision"


class FunnelStage(str, Enum):
    """Marketing funnel stage."""
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    PURCHASE = "purchase"


class QueryIntent(str, Enum):
    """Search query intent type."""
    COMMERCIAL = "Commercial"
    INFORMATIONAL = "Informational"
    NAVIGATIONAL = "Navigational"
    TRANSACTIONAL = "Transactional"


# ==================== Core Classification Schemas ====================


class UserIntent(BaseModel):
    """
    User intent classification structure from ARCHITECTURE.md.

    This is the core classification output for each prompt.
    """
    intent_type: IntentType = Field(
        ...,
        description="What the user is trying to accomplish",
    )
    funnel_stage: FunnelStage = Field(
        ...,
        description="Where they are in the buying journey",
    )
    buying_signal: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How close to purchase decision (0.0-1.0)",
    )
    trust_need: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How much authority/proof required (0.0-1.0)",
    )

    model_config = {"use_enum_values": True}


class ClassificationResult(UserIntent):
    """
    Extended classification result with additional metadata.
    """
    query_intent: QueryIntent | None = Field(
        default=None,
        description="Commercial, Informational, Navigational, or Transactional",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Classifier confidence score",
    )
    reasoning: str | None = Field(
        default=None,
        description="Brief explanation for the classification",
    )


class PromptClassificationInput(BaseModel):
    """Input for classifying a single prompt."""
    prompt_id: UUID
    prompt_text: str = Field(..., min_length=5)
    conversation_topic: str | None = None
    conversation_context: str | None = None
    icp_name: str | None = None
    icp_pain_points: list[str] | None = None


class PromptClassificationOutput(BaseModel):
    """Output from classifying a single prompt."""
    prompt_id: UUID
    prompt_text: str
    classification: ClassificationResult
    classified_at: datetime
    classifier_version: str


class BatchClassificationInput(BaseModel):
    """Input for batch classification of multiple prompts."""
    prompts: list[PromptClassificationInput] = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider to use (openai, anthropic)",
    )


class BatchClassificationOutput(BaseModel):
    """Output from batch classification."""
    total: int
    successful: int
    failed: int
    classifications: list[PromptClassificationOutput]
    errors: list[dict] | None = None


# ==================== API Request/Response Schemas ====================


class ClassifyPromptsRequest(BaseModel):
    """Request to classify prompts for a website."""
    force_reclassify: bool = Field(
        default=False,
        description="Whether to reclassify already classified prompts",
    )
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider to use (openai, anthropic)",
    )
    icp_ids: list[UUID] | None = Field(
        default=None,
        description="Filter to specific ICPs (optional)",
    )


class ClassifyJobResponse(BaseModel):
    """Response when a classification job is queued."""
    job_id: UUID
    website_id: UUID
    status: str = "queued"
    total_prompts: int
    message: str = "Classification job queued"


class ClassificationJobStatus(BaseModel):
    """Status of a classification job."""
    job_id: UUID
    website_id: UUID
    status: str
    progress: float = 0.0
    total_prompts: int = 0
    classified_prompts: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


# ==================== Classification Query Schemas ====================


class ClassificationSummary(BaseModel):
    """Summary statistics for classifications."""
    total: int
    by_intent_type: dict[str, int]
    by_funnel_stage: dict[str, int]
    by_query_intent: dict[str, int]
    avg_buying_signal: float
    avg_trust_need: float


class ClassificationFilter(BaseModel):
    """Filters for querying classifications."""
    intent_type: IntentType | None = None
    funnel_stage: FunnelStage | None = None
    min_buying_signal: float | None = Field(default=None, ge=0.0, le=1.0)
    max_buying_signal: float | None = Field(default=None, ge=0.0, le=1.0)
    min_trust_need: float | None = Field(default=None, ge=0.0, le=1.0)
    max_trust_need: float | None = Field(default=None, ge=0.0, le=1.0)
    icp_id: UUID | None = None


class ClassifiedPromptResponse(BaseModel):
    """Response for a single classified prompt."""
    prompt_id: UUID
    prompt_text: str
    conversation_id: UUID
    icp_id: UUID
    classification: ClassificationResult
    classified_at: datetime | None = None


class ClassificationsListResponse(BaseModel):
    """Response containing list of classifications with summary."""
    data: list[ClassifiedPromptResponse]
    summary: ClassificationSummary
    pagination: dict | None = None


# ==================== LLM Response Parsing Schemas ====================


class LLMClassificationResponse(BaseModel):
    """
    Expected structure of LLM classification response.
    Used for parsing JSON responses from the LLM.
    """
    intent_type: str = Field(
        ...,
        description="informational, evaluation, or decision",
    )
    funnel_stage: str = Field(
        ...,
        description="awareness, consideration, or purchase",
    )
    buying_signal: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )
    trust_need: float = Field(
        ...,
        ge=0.0,
        le=1.0,
    )
    query_intent: str | None = Field(
        default=None,
        description="Commercial, Informational, Navigational, or Transactional",
    )
    reasoning: str | None = Field(
        default=None,
        description="Brief explanation for the classification",
    )

    @field_validator("intent_type")
    @classmethod
    def validate_intent_type(cls, v: str) -> str:
        """Normalize and validate intent type."""
        v = v.lower().strip()
        valid = {"informational", "evaluation", "decision"}
        if v not in valid:
            raise ValueError(f"Invalid intent_type: {v}. Must be one of {valid}")
        return v

    @field_validator("funnel_stage")
    @classmethod
    def validate_funnel_stage(cls, v: str) -> str:
        """Normalize and validate funnel stage."""
        v = v.lower().strip()
        valid = {"awareness", "consideration", "purchase"}
        if v not in valid:
            raise ValueError(f"Invalid funnel_stage: {v}. Must be one of {valid}")
        return v

    @field_validator("query_intent")
    @classmethod
    def validate_query_intent(cls, v: str | None) -> str | None:
        """Normalize and validate query intent."""
        if v is None:
            return None
        v = v.strip().title()
        valid = {"Commercial", "Informational", "Navigational", "Transactional"}
        if v not in valid:
            # Try to map common variations
            mapping = {
                "commercial": "Commercial",
                "info": "Informational",
                "informational": "Informational",
                "nav": "Navigational",
                "navigational": "Navigational",
                "transaction": "Transactional",
                "transactional": "Transactional",
            }
            v = mapping.get(v.lower(), v)
        return v if v in valid else None

    def to_classification_result(self) -> ClassificationResult:
        """Convert to ClassificationResult."""
        return ClassificationResult(
            intent_type=IntentType(self.intent_type),
            funnel_stage=FunnelStage(self.funnel_stage),
            buying_signal=self.buying_signal,
            trust_need=self.trust_need,
            query_intent=QueryIntent(self.query_intent) if self.query_intent else None,
            confidence_score=0.85,  # Default confidence for LLM classifications
            reasoning=self.reasoning,
        )


class BatchLLMClassificationResponse(BaseModel):
    """Expected structure for batch classification response from LLM."""
    classifications: list[LLMClassificationResponse]
