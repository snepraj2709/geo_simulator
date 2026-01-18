"""
Pydantic schemas for Competitive Substitution Engine.

Defines data models for competitive analysis requests, responses,
and internal data structures.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMProviderEnum(str, Enum):
    """LLM providers for competitive analysis."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    PERPLEXITY = "perplexity"
    ALL = "all"


class CompetitorRelationshipType(str, Enum):
    """Types of competitor relationships."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    SUBSTITUTE = "substitute"


class OpportunityType(str, Enum):
    """Types of competitive opportunities."""

    VISIBILITY_GAP = "visibility_gap"
    RECOMMENDATION_GAP = "recommendation_gap"
    POSITION_IMPROVEMENT = "position_improvement"
    PROVIDER_EXPANSION = "provider_expansion"
    SUBSTITUTION_DEFENSE = "substitution_defense"


# ==================== Request Schemas ====================


class SubstitutionAnalysisRequest(BaseModel):
    """Request to analyze substitution patterns for a website."""

    tracked_brand_name: str | None = Field(
        default=None,
        description="Primary brand to track (optional, uses website's tracked brand)",
    )
    llm_providers: list[LLMProviderEnum] | None = Field(
        default=None,
        description="LLM providers to analyze (None = all)",
    )
    period_start: date | None = Field(
        default=None,
        description="Start of analysis period",
    )
    period_end: date | None = Field(
        default=None,
        description="End of analysis period",
    )
    min_occurrence_count: int = Field(
        default=2,
        ge=1,
        description="Minimum occurrences to include in patterns",
    )


class ShareOfVoiceRequest(BaseModel):
    """Request for share of voice analysis."""

    llm_provider: LLMProviderEnum | None = Field(
        default=None,
        description="Filter by LLM provider (None = aggregate all)",
    )
    period_start: date | None = Field(
        default=None,
        description="Start of analysis period",
    )
    period_end: date | None = Field(
        default=None,
        description="End of analysis period",
    )
    include_competitors: bool = Field(
        default=True,
        description="Include competitor comparison data",
    )
    top_n_competitors: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of top competitors to include",
    )


class SubstitutionPatternsRequest(BaseModel):
    """Request to get substitution patterns."""

    brand_name: str | None = Field(
        default=None,
        description="Brand to get substitution patterns for (missing brand)",
    )
    llm_provider: LLMProviderEnum | None = Field(
        default=None,
        description="Filter by LLM provider",
    )
    min_count: int = Field(
        default=1,
        ge=1,
        description="Minimum occurrence count",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum patterns to return",
    )


# ==================== Response Schemas ====================


class BrandMetrics(BaseModel):
    """Metrics for a single brand."""

    brand_id: uuid.UUID | None = None
    brand_name: str
    normalized_name: str
    mention_count: int = 0
    recommendation_count: int = 0
    first_position_count: int = 0
    total_responses: int = 0
    avg_position: float | None = None
    visibility_score: float = 0.0
    trust_score: float = 0.0
    recommendation_rate: float = 0.0
    share_of_voice: float = 0.0


class ProviderMetrics(BaseModel):
    """Metrics breakdown by LLM provider."""

    provider: str
    mention_count: int = 0
    recommendation_count: int = 0
    first_position_count: int = 0
    total_responses: int = 0
    avg_position: float | None = None
    visibility_score: float = 0.0
    recommendation_rate: float = 0.0


class ShareOfVoiceResponse(BaseModel):
    """Share of voice analysis response."""

    brand_name: str
    brand_id: uuid.UUID | None = None
    overall_metrics: BrandMetrics
    by_provider: list[ProviderMetrics] = Field(default_factory=list)
    competitors: list[BrandMetrics] = Field(default_factory=list)
    period_start: date | None = None
    period_end: date | None = None
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class SubstituteInfo(BaseModel):
    """Information about a substitute brand."""

    brand_id: uuid.UUID | None = None
    brand_name: str
    normalized_name: str
    occurrence_count: int
    avg_position: float | None = None
    providers: list[str] = Field(default_factory=list)
    substitution_rate: float = 0.0


class SubstitutionPatternResponse(BaseModel):
    """Response for substitution pattern query."""

    missing_brand_name: str
    missing_brand_id: uuid.UUID | None = None
    total_absence_count: int = 0
    substitutes: list[SubstituteInfo] = Field(default_factory=list)
    top_substitute: SubstituteInfo | None = None


class CompetitiveGap(BaseModel):
    """A competitive gap identified in analysis."""

    gap_type: OpportunityType
    description: str
    severity: float = Field(ge=0.0, le=1.0, description="Gap severity (0-1)")
    competitor_name: str | None = None
    provider: str | None = None
    current_value: float | None = None
    target_value: float | None = None
    improvement_potential: float | None = None


class Opportunity(BaseModel):
    """A competitive opportunity."""

    opportunity_type: OpportunityType
    description: str
    score: float = Field(ge=0.0, le=100.0, description="Opportunity score (0-100)")
    priority: int = Field(ge=1, le=5, description="Priority level (1=highest)")
    related_competitors: list[str] = Field(default_factory=list)
    related_providers: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    potential_impact: str | None = None


class SubstitutionAnalysisResponse(BaseModel):
    """Full substitution analysis response."""

    website_id: uuid.UUID
    tracked_brand: str
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Share of voice
    share_of_voice: ShareOfVoiceResponse

    # Substitution patterns
    substitution_patterns: list[SubstitutionPatternResponse] = Field(default_factory=list)
    brands_substituting_tracked: list[SubstituteInfo] = Field(default_factory=list)
    brands_tracked_substitutes: list[SubstituteInfo] = Field(default_factory=list)

    # Competitive gaps
    competitive_gaps: list[CompetitiveGap] = Field(default_factory=list)

    # Opportunities
    opportunities: list[Opportunity] = Field(default_factory=list)
    overall_opportunity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall opportunity score (0-100)",
    )

    # Summary
    summary: dict[str, Any] = Field(default_factory=dict)


# ==================== Storage Schemas ====================


class ShareOfVoiceCreate(BaseModel):
    """Schema for creating ShareOfVoice record."""

    website_id: uuid.UUID
    brand_id: uuid.UUID
    llm_provider: str
    mention_count: int = 0
    recommendation_count: int = 0
    first_position_count: int = 0
    total_responses: int = 0
    visibility_score: Decimal | None = None
    trust_score: Decimal | None = None
    recommendation_rate: Decimal | None = None
    period_start: date
    period_end: date


class SubstitutionPatternCreate(BaseModel):
    """Schema for creating SubstitutionPattern record."""

    website_id: uuid.UUID
    missing_brand_id: uuid.UUID
    substitute_brand_id: uuid.UUID
    occurrence_count: int = 1
    avg_position: Decimal | None = None
    llm_provider: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class CompetitorRelationshipCreate(BaseModel):
    """Schema for creating CompetitorRelationship record."""

    website_id: uuid.UUID
    primary_brand_id: uuid.UUID
    competitor_brand_id: uuid.UUID
    relationship_type: CompetitorRelationshipType | None = None


# ==================== API Response Schemas ====================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str = "competitive-substitution-engine"
    version: str = "1.0.0"


class AnalysisJobResponse(BaseModel):
    """Response for async analysis job."""

    job_id: uuid.UUID
    status: str
    message: str
    estimated_completion: datetime | None = None


# ==================== Graph Query Results ====================


class GraphCoMention(BaseModel):
    """Co-mention data from graph."""

    brand_name: str
    normalized_name: str
    co_mention_count: int
    avg_position_delta: float | None = None
    providers: list[str] = Field(default_factory=list)


class GraphSubstitution(BaseModel):
    """Substitution data from graph."""

    missing_brand: str
    substitute_brand: str
    occurrence_count: int
    avg_position: float | None = None
    providers: list[str] = Field(default_factory=list)
