"""
Pydantic schemas for Brand Presence Detector.

Defines data models for brand presence detection requests, responses,
and internal data structures following DATA_MODEL.md specifications.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BrandPresenceState(str, Enum):
    """
    Brand presence states in LLM response.

    From ARCHITECTURE.md:
    - ignored: Brand not mentioned at all
    - mentioned: Brand name appears but without context
    - trusted: Brand cited as authority without sales push
    - recommended: Brand with clear call-to-action
    - compared: Brand in neutral evaluation context
    """

    IGNORED = "ignored"
    MENTIONED = "mentioned"
    TRUSTED = "trusted"
    RECOMMENDED = "recommended"
    COMPARED = "compared"


class BeliefType(str, Enum):
    """
    Type of belief installed by LLM response.

    From DATA_MODEL.md:
    - truth: epistemic clarity, neutrality
    - superiority: better than alternatives
    - outcome: ROI, performance, results
    - transaction: buy now, act
    - identity: people like you use this
    - social_proof: others chose this
    """

    TRUTH = "truth"
    SUPERIORITY = "superiority"
    OUTCOME = "outcome"
    TRANSACTION = "transaction"
    IDENTITY = "identity"
    SOCIAL_PROOF = "social_proof"


# ==================== Request Schemas ====================


class BrandDetectionRequest(BaseModel):
    """Request to detect brand presence in text."""

    response_text: str = Field(
        ...,
        description="LLM response text to analyze",
        min_length=1,
    )
    known_brands: list[str] | None = Field(
        default=None,
        description="Optional list of known brand names to look for",
    )
    tracked_brand: str | None = Field(
        default=None,
        description="The user's own brand to specifically track",
    )


class BatchDetectionRequest(BaseModel):
    """Request for batch brand presence detection."""

    responses: list[BrandDetectionRequest]
    known_brands: list[str] | None = None
    tracked_brand: str | None = None


class LLMResponseAnalysisRequest(BaseModel):
    """Request to analyze an LLM response for brand presence."""

    llm_response_id: uuid.UUID
    simulation_run_id: uuid.UUID | None = None
    prompt_id: uuid.UUID | None = None
    llm_provider: str
    llm_model: str
    response_text: str
    known_brands: list[str] | None = None
    tracked_brand: str | None = None


# ==================== Response Schemas ====================


class BrandPresenceResult(BaseModel):
    """
    Brand presence detection result for a single brand.

    Implements LLMBrandState from DATA_MODEL.md:
    - presence: "ignored" | "mentioned" | "trusted" | "recommended" | "compared"
    - position_rank: number | null
    """

    brand_name: str = Field(..., description="Original brand name as detected")
    normalized_name: str = Field(..., description="Normalized (lowercase) brand name")
    presence: BrandPresenceState = Field(
        ...,
        description="Dominant presence state for this brand",
    )
    position_rank: int | None = Field(
        default=None,
        description="Position in response (1 = first mentioned)",
    )
    belief_sold: BeliefType | None = Field(
        default=None,
        description="Type of belief installed for this brand",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the classification",
    )
    context_snippet: str | None = Field(
        default=None,
        description="Text context around the brand mention",
        max_length=500,
    )
    detection_signals: list[str] = Field(
        default_factory=list,
        description="Signals that contributed to the classification",
    )

    class Config:
        from_attributes = True


class BrandDetectionResponse(BaseModel):
    """Response from brand presence detection."""

    brands: list[BrandPresenceResult] = Field(
        default_factory=list,
        description="List of detected brands with their presence states",
    )
    tracked_brand_result: BrandPresenceResult | None = Field(
        default=None,
        description="Result for the specifically tracked brand",
    )
    total_brands_found: int = Field(
        default=0,
        description="Total number of brands detected",
    )
    analysis_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the analysis",
    )


class BatchDetectionResponse(BaseModel):
    """Response from batch brand detection."""

    results: list[BrandDetectionResponse]
    total_responses_analyzed: int
    total_brands_found: int
    summary: dict[str, Any] = Field(default_factory=dict)


# ==================== Storage Schemas ====================


class LLMBrandStateCreate(BaseModel):
    """Schema for creating an LLMBrandState record."""

    llm_response_id: uuid.UUID
    brand_id: uuid.UUID
    presence: BrandPresenceState
    position_rank: int | None = None
    belief_sold: BeliefType | None = None


class LLMBrandStateResponse(BaseModel):
    """Schema for LLMBrandState response."""

    id: uuid.UUID
    llm_response_id: uuid.UUID
    brand_id: uuid.UUID
    presence: str
    position_rank: int | None
    belief_sold: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class BrandCreate(BaseModel):
    """Schema for creating a Brand record."""

    name: str
    normalized_name: str
    domain: str | None = None
    industry: str | None = None
    is_tracked: bool = False


class BrandResponse(BaseModel):
    """Schema for Brand response."""

    id: uuid.UUID
    name: str
    normalized_name: str
    domain: str | None
    industry: str | None
    is_tracked: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Analysis Schemas ====================


class PresenceBreakdown(BaseModel):
    """Breakdown of presence states."""

    ignored: int = 0
    mentioned: int = 0
    trusted: int = 0
    recommended: int = 0
    compared: int = 0


class BeliefDistribution(BaseModel):
    """Distribution of belief types."""

    truth: int = 0
    superiority: int = 0
    outcome: int = 0
    transaction: int = 0
    identity: int = 0
    social_proof: int = 0


class BrandAnalysisSummary(BaseModel):
    """Summary of brand analysis across multiple responses."""

    brand_id: uuid.UUID
    brand_name: str
    total_appearances: int = 0
    presence_breakdown: PresenceBreakdown = Field(default_factory=PresenceBreakdown)
    belief_distribution: BeliefDistribution = Field(default_factory=BeliefDistribution)
    avg_position: float | None = None
    recommendation_rate: float = 0.0
    by_provider: dict[str, dict[str, Any]] = Field(default_factory=dict)


# ==================== API Response Schemas ====================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "brand-presence-detector"
    version: str = "1.0.0"


class DetectionStatsResponse(BaseModel):
    """Detection statistics response."""

    total_detections: int = 0
    brands_detected: int = 0
    presence_distribution: PresenceBreakdown = Field(default_factory=PresenceBreakdown)
    belief_distribution: BeliefDistribution = Field(default_factory=BeliefDistribution)
    avg_brands_per_response: float = 0.0
