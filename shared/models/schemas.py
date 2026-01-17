"""
Pydantic schemas for API validation and serialization.

This module contains all Pydantic models for validating API requests
and responses. Schemas are organized by entity and follow naming conventions:
- *Base: Common fields shared between create and response
- *Create: Fields required to create an entity
- *Update: Fields that can be updated (usually optional)
- *Response: Fields returned in API responses
- *InDB: Full model including database fields
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# ============================================================================
# Base Configuration
# ============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


# ============================================================================
# Organization Schemas
# ============================================================================

class OrganizationBase(BaseSchema):
    """Base organization fields."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan_type: str = Field(default="free", pattern=r"^(free|pro|enterprise)$")


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    pass


class OrganizationUpdate(BaseSchema):
    """Schema for updating an organization."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan_type: str | None = Field(default=None, pattern=r"^(free|pro|enterprise)$")


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseSchema):
    """Base user fields."""

    email: str = Field(..., max_length=255)
    name: str | None = Field(default=None, max_length=255)
    role: str = Field(default="member", pattern=r"^(admin|member|viewer)$")


class UserCreate(UserBase):
    """Schema for creating a user."""

    organization_id: uuid.UUID
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseSchema):
    """Schema for updating a user."""

    name: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, pattern=r"^(admin|member|viewer)$")
    is_active: bool | None = None


class UserResponse(UserBase):
    """Schema for user response."""

    id: uuid.UUID
    organization_id: uuid.UUID
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Website Schemas
# ============================================================================

class WebsiteBase(BaseSchema):
    """Base website fields."""

    url: HttpUrl
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None


class WebsiteCreate(WebsiteBase):
    """Schema for creating a website."""

    scrape_depth: int = Field(default=3, ge=1, le=10)


class WebsiteUpdate(BaseSchema):
    """Schema for updating a website."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    scrape_depth: int | None = Field(default=None, ge=1, le=10)


class WebsiteResponse(WebsiteBase):
    """Schema for website response."""

    id: uuid.UUID
    organization_id: uuid.UUID
    domain: str
    status: str
    last_scraped_at: datetime | None
    last_hard_scrape_at: datetime | None
    scrape_depth: int
    created_at: datetime
    updated_at: datetime


class WebsiteListResponse(BaseSchema):
    """Schema for paginated website list."""

    websites: list[WebsiteResponse]
    total: int
    page: int = 1
    limit: int = 20


# ============================================================================
# Scraped Page Schemas
# ============================================================================

class ScrapedPageBase(BaseSchema):
    """Base scraped page fields."""

    url: str = Field(..., max_length=2048)
    title: str | None = Field(default=None, max_length=512)
    meta_description: str | None = None
    page_type: str | None = Field(default=None, max_length=50)


class ScrapedPageResponse(ScrapedPageBase):
    """Schema for scraped page response."""

    id: uuid.UUID
    website_id: uuid.UUID
    url_hash: str
    content_text: str | None = None
    word_count: int | None = None
    http_status: int | None = None
    scraped_at: datetime


# ============================================================================
# Website Analysis Schemas
# ============================================================================

class WebsiteAnalysisBase(BaseSchema):
    """Base website analysis fields."""

    industry: str | None = Field(default=None, max_length=255)
    business_model: str | None = Field(default=None, pattern=r"^(b2b|b2c|b2b2c|marketplace)$")
    primary_offerings: list[dict[str, Any]] | None = None
    value_propositions: list[str] | None = None
    target_markets: list[str] | None = None
    competitors_mentioned: list[str] | None = None


class WebsiteAnalysisResponse(WebsiteAnalysisBase):
    """Schema for website analysis response."""

    id: uuid.UUID
    website_id: uuid.UUID
    analyzed_at: datetime


# ============================================================================
# ICP Schemas
# ============================================================================

class DemographicsSchema(BaseSchema):
    """Schema for ICP demographics."""

    age_range: str | None = None
    gender: str | None = None
    location: str | None = None
    income_level: str | None = None
    education: str | None = None


class ProfessionalProfileSchema(BaseSchema):
    """Schema for ICP professional profile."""

    job_titles: list[str] | None = None
    company_size: str | None = None
    industry: str | None = None
    seniority: str | None = None


class MotivationsSchema(BaseSchema):
    """Schema for ICP motivations."""

    primary: str | None = None
    secondary: str | None = None


class ICPBase(BaseSchema):
    """Base ICP fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    sequence_number: int = Field(..., ge=1, le=5)
    demographics: dict[str, Any]
    professional_profile: dict[str, Any]
    pain_points: list[str]
    goals: list[str]
    motivations: dict[str, Any]
    objections: list[str] | None = None
    decision_factors: list[str] | None = None
    information_sources: list[str] | None = None
    buying_journey_stage: str | None = Field(default=None, max_length=50)


class ICPCreate(ICPBase):
    """Schema for creating an ICP."""

    website_id: uuid.UUID


class ICPUpdate(BaseSchema):
    """Schema for updating an ICP."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    demographics: dict[str, Any] | None = None
    professional_profile: dict[str, Any] | None = None
    pain_points: list[str] | None = None
    goals: list[str] | None = None
    motivations: dict[str, Any] | None = None
    objections: list[str] | None = None
    decision_factors: list[str] | None = None
    information_sources: list[str] | None = None
    buying_journey_stage: str | None = None
    is_active: bool | None = None


class ICPResponse(ICPBase):
    """Schema for ICP response."""

    id: uuid.UUID
    website_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationBase(BaseSchema):
    """Base conversation fields."""

    topic: str = Field(..., min_length=1, max_length=255)
    context: str | None = None
    expected_outcome: str | None = None
    is_core_conversation: bool = False
    sequence_number: int = Field(..., ge=1, le=10)


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""

    website_id: uuid.UUID
    icp_id: uuid.UUID


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""

    id: uuid.UUID
    website_id: uuid.UUID
    icp_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Prompt Schemas
# ============================================================================

class PromptBase(BaseSchema):
    """Base prompt fields."""

    prompt_text: str = Field(..., min_length=1)
    prompt_type: str = Field(default="primary", pattern=r"^(primary|follow_up|clarification)$")
    sequence_order: int = Field(..., ge=1)


class PromptCreate(PromptBase):
    """Schema for creating a prompt."""

    conversation_id: uuid.UUID


class PromptResponse(PromptBase):
    """Schema for prompt response."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    classification: "PromptClassificationResponse | None" = None


# ============================================================================
# Prompt Classification Schemas
# ============================================================================

class PromptClassificationBase(BaseSchema):
    """Base prompt classification fields."""

    intent_type: str = Field(..., pattern=r"^(informational|evaluation|decision)$")
    funnel_stage: str = Field(..., pattern=r"^(awareness|consideration|purchase)$")
    buying_signal: Decimal = Field(..., ge=0, le=1, decimal_places=2)
    trust_need: Decimal = Field(..., ge=0, le=1, decimal_places=2)
    query_intent: str | None = Field(
        default=None,
        pattern=r"^(Commercial|Informational|Navigational|Transactional)$"
    )
    confidence_score: Decimal | None = Field(default=None, ge=0, le=1, decimal_places=2)


class PromptClassificationCreate(PromptClassificationBase):
    """Schema for creating a prompt classification."""

    prompt_id: uuid.UUID
    classifier_version: str | None = None


class PromptClassificationResponse(PromptClassificationBase):
    """Schema for prompt classification response."""

    id: uuid.UUID
    prompt_id: uuid.UUID
    classified_at: datetime | None
    classifier_version: str | None


# ============================================================================
# Simulation Schemas
# ============================================================================

class SimulationRunBase(BaseSchema):
    """Base simulation run fields."""

    total_prompts: int | None = None


class SimulationRunCreate(SimulationRunBase):
    """Schema for creating a simulation run."""

    website_id: uuid.UUID


class SimulationRunResponse(SimulationRunBase):
    """Schema for simulation run response."""

    id: uuid.UUID
    website_id: uuid.UUID
    status: str
    completed_prompts: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class SimulationSummary(BaseSchema):
    """Schema for simulation summary."""

    simulation_run_id: uuid.UUID
    website_id: uuid.UUID
    total_prompts: int
    responses_generated: int
    providers: list[str]
    status: str


# ============================================================================
# LLM Response Schemas
# ============================================================================

class LLMResponseBase(BaseSchema):
    """Base LLM response fields."""

    llm_provider: str = Field(..., pattern=r"^(openai|google|anthropic|perplexity)$")
    llm_model: str = Field(..., max_length=100)
    response_text: str
    response_tokens: int | None = None
    latency_ms: int | None = None
    brands_mentioned: list[str] | None = None


class LLMResponseCreate(LLMResponseBase):
    """Schema for creating an LLM response."""

    simulation_run_id: uuid.UUID
    prompt_id: uuid.UUID


class LLMResponseResponse(LLMResponseBase):
    """Schema for LLM response response."""

    id: uuid.UUID
    simulation_run_id: uuid.UUID
    prompt_id: uuid.UUID
    created_at: datetime


# ============================================================================
# Brand Schemas
# ============================================================================

class BrandBase(BaseSchema):
    """Base brand fields."""

    name: str = Field(..., min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=255)


class BrandCreate(BrandBase):
    """Schema for creating a brand."""

    is_tracked: bool = False


class BrandUpdate(BaseSchema):
    """Schema for updating a brand."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = None
    industry: str | None = None
    is_tracked: bool | None = None


class BrandResponse(BrandBase):
    """Schema for brand response."""

    id: uuid.UUID
    normalized_name: str
    is_tracked: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Brand State Schemas
# ============================================================================

class LLMBrandStateBase(BaseSchema):
    """Base LLM brand state fields."""

    presence: str = Field(..., pattern=r"^(ignored|mentioned|trusted|recommended|compared)$")
    position_rank: int | None = Field(default=None, ge=1)
    belief_sold: str | None = Field(
        default=None,
        pattern=r"^(truth|superiority|outcome|transaction|identity|social_proof)$"
    )


class LLMBrandStateCreate(LLMBrandStateBase):
    """Schema for creating a brand state."""

    llm_response_id: uuid.UUID
    brand_id: uuid.UUID


class LLMBrandStateResponse(LLMBrandStateBase):
    """Schema for brand state response."""

    id: uuid.UUID
    llm_response_id: uuid.UUID
    brand_id: uuid.UUID
    created_at: datetime


# ============================================================================
# Belief Map Schemas
# ============================================================================

class LLMAnswerBeliefMapResponse(BaseSchema):
    """Schema for belief map response."""

    id: uuid.UUID
    llm_response_id: uuid.UUID
    prompt_classification_id: uuid.UUID | None
    brand_id: uuid.UUID
    intent_type: str | None
    funnel_stage: str | None
    buying_signal: Decimal | None
    trust_need: Decimal | None
    presence: str | None
    position_rank: int | None
    belief_sold: str | None
    llm_provider: str | None
    created_at: datetime


# ============================================================================
# Competitive Analysis Schemas
# ============================================================================

class CompetitorRelationshipBase(BaseSchema):
    """Base competitor relationship fields."""

    relationship_type: str | None = Field(
        default=None,
        pattern=r"^(direct|indirect|substitute)$"
    )


class CompetitorRelationshipCreate(CompetitorRelationshipBase):
    """Schema for creating a competitor relationship."""

    website_id: uuid.UUID
    primary_brand_id: uuid.UUID
    competitor_brand_id: uuid.UUID


class CompetitorRelationshipResponse(CompetitorRelationshipBase):
    """Schema for competitor relationship response."""

    id: uuid.UUID
    website_id: uuid.UUID
    primary_brand_id: uuid.UUID
    competitor_brand_id: uuid.UUID
    created_at: datetime


# ============================================================================
# Share of Voice Schemas
# ============================================================================

class ShareOfVoiceBase(BaseSchema):
    """Base share of voice fields."""

    llm_provider: str = Field(..., pattern=r"^(openai|google|anthropic|perplexity)$")
    mention_count: int = Field(default=0, ge=0)
    recommendation_count: int = Field(default=0, ge=0)
    first_position_count: int = Field(default=0, ge=0)
    total_responses: int = Field(default=0, ge=0)
    visibility_score: Decimal | None = Field(default=None, ge=0, le=100)
    trust_score: Decimal | None = Field(default=None, ge=0, le=100)
    recommendation_rate: Decimal | None = Field(default=None, ge=0, le=100)
    period_start: date
    period_end: date


class ShareOfVoiceCreate(ShareOfVoiceBase):
    """Schema for creating share of voice."""

    website_id: uuid.UUID
    brand_id: uuid.UUID


class ShareOfVoiceResponse(ShareOfVoiceBase):
    """Schema for share of voice response."""

    id: uuid.UUID
    website_id: uuid.UUID
    brand_id: uuid.UUID
    created_at: datetime


# ============================================================================
# Substitution Pattern Schemas
# ============================================================================

class SubstitutionPatternBase(BaseSchema):
    """Base substitution pattern fields."""

    occurrence_count: int = Field(default=1, ge=1)
    avg_position: Decimal | None = Field(default=None, ge=1)
    llm_provider: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class SubstitutionPatternCreate(SubstitutionPatternBase):
    """Schema for creating a substitution pattern."""

    website_id: uuid.UUID
    missing_brand_id: uuid.UUID
    substitute_brand_id: uuid.UUID


class SubstitutionPatternResponse(SubstitutionPatternBase):
    """Schema for substitution pattern response."""

    id: uuid.UUID
    website_id: uuid.UUID
    missing_brand_id: uuid.UUID
    substitute_brand_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Summary & Analytics Schemas
# ============================================================================

class BrandSummary(BaseSchema):
    """Summary stats for a single brand."""

    brand_name: str
    mention_count: int
    recommendation_count: int
    avg_position: float | None


class WebsiteSummaryResponse(BaseSchema):
    """Aggregated summary for a website."""

    website_id: uuid.UUID
    total_simulations: int
    total_responses: int
    total_mentions: int
    total_recommendations: int
    top_competitors: list[BrandSummary]
    by_provider: dict[str, dict[str, int]]


class BootstrapResponse(BaseSchema):
    """Response from bootstrap operation."""

    website_id: uuid.UUID
    icps_created: int
    conversations_created: int
    prompts_created: int
    message: str


# ============================================================================
# Forward References
# ============================================================================

# Update forward references
PromptResponse.model_rebuild()
