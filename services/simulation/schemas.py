"""
Pydantic schemas for the LLM Simulation Service.

Defines data models for simulation requests, responses, and internal data structures.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ==================== Enums ====================


class LLMProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"


class BrandPresenceType(str, Enum):
    """Brand presence state in LLM response."""

    IGNORED = "ignored"
    MENTIONED = "mentioned"
    TRUSTED = "trusted"
    RECOMMENDED = "recommended"
    COMPARED = "compared"


class BeliefType(str, Enum):
    """Type of belief installed by LLM response."""

    TRUTH = "truth"
    SUPERIORITY = "superiority"
    OUTCOME = "outcome"
    TRANSACTION = "transaction"
    IDENTITY = "identity"
    SOCIAL_PROOF = "social_proof"


class QueryIntentType(str, Enum):
    """Search query intent type for intent ranking."""

    COMMERCIAL = "Commercial"
    INFORMATIONAL = "Informational"
    NAVIGATIONAL = "Navigational"
    TRANSACTIONAL = "Transactional"


# ==================== Prompt Queue Schemas ====================


class PromptQueueItem(BaseModel):
    """Item in the prompt queue for processing."""

    prompt_id: uuid.UUID
    prompt_text: str
    conversation_id: uuid.UUID | None = None
    icp_id: uuid.UUID | None = None
    website_id: uuid.UUID
    classification: "PromptClassificationData | None" = None
    priority: int = Field(default=0, description="Higher priority = processed first")
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    class Config:
        from_attributes = True


class PromptClassificationData(BaseModel):
    """Classification data for a prompt."""

    intent_type: str  # informational, evaluation, decision
    funnel_stage: str  # awareness, consideration, purchase
    buying_signal: Decimal = Field(ge=0, le=1)
    trust_need: Decimal = Field(ge=0, le=1)
    query_intent: QueryIntentType | None = None


# ==================== LLM Response Schemas ====================


class LLMQueryRequest(BaseModel):
    """Request to query an LLM provider."""

    prompt_text: str
    provider: LLMProviderType
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=32000)
    system_prompt: str | None = None


class LLMQueryResponse(BaseModel):
    """Response from an LLM provider."""

    provider: LLMProviderType
    model: str
    response_text: str
    tokens_used: int = 0
    latency_ms: int = 0
    success: bool = True
    error: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class NormalizedLLMResponse(BaseModel):
    """Normalized LLM response with extracted metadata."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    simulation_run_id: uuid.UUID
    prompt_id: uuid.UUID
    provider: LLMProviderType
    model: str
    response_text: str
    tokens_used: int = 0
    latency_ms: int = 0
    brands_mentioned: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== Brand Extraction Schemas ====================


class BrandMention(BaseModel):
    """A brand mention extracted from LLM response."""

    brand_name: str
    normalized_name: str
    presence: BrandPresenceType
    position_rank: int = Field(description="Position in response, 1 = first")
    belief_sold: BeliefType | None = None
    context_snippet: str = Field(
        description="Text surrounding the brand mention",
        max_length=500,
    )
    confidence: float = Field(ge=0, le=1, default=1.0)


class IntentRanking(BaseModel):
    """Intent ranking for a response."""

    query_intent: QueryIntentType
    confidence: float = Field(ge=0, le=1)


class BrandExtractionResult(BaseModel):
    """Result of brand extraction from an LLM response."""

    response_id: uuid.UUID
    brands: list[BrandMention] = Field(default_factory=list)
    intent_ranking: IntentRanking | None = None
    contextual_framing: dict[str, str] = Field(
        default_factory=dict,
        description="Brand name to contextual framing description",
    )


# ==================== Simulation Schemas ====================


class PromptFilter(BaseModel):
    """Filter for selecting prompts to simulate."""

    icp_ids: list[uuid.UUID] | None = None
    intent_types: list[str] | None = None
    funnel_stages: list[str] | None = None
    core_only: bool = False
    min_buying_signal: float | None = None
    min_trust_need: float | None = None


class SimulationRequest(BaseModel):
    """Request to start a simulation."""

    website_id: uuid.UUID
    llm_providers: list[LLMProviderType] = Field(
        default=[
            LLMProviderType.OPENAI,
            LLMProviderType.GOOGLE,
            LLMProviderType.ANTHROPIC,
            LLMProviderType.PERPLEXITY,
        ]
    )
    prompt_filter: PromptFilter | None = None
    parallel_workers: int = Field(default=4, ge=1, le=20)


class SimulationProgress(BaseModel):
    """Progress update for a running simulation."""

    simulation_id: uuid.UUID
    status: str
    total_prompts: int
    completed_prompts: int
    failed_prompts: int = 0
    current_provider: str | None = None
    estimated_remaining_seconds: int | None = None


class SimulationResult(BaseModel):
    """Final result of a completed simulation."""

    simulation_id: uuid.UUID
    status: str
    total_prompts: int
    completed_prompts: int
    failed_prompts: int
    total_responses: int
    brands_discovered: int
    started_at: datetime
    completed_at: datetime
    duration_seconds: int
    responses_by_provider: dict[str, int] = Field(default_factory=dict)


# ==================== Aggregated Metrics Schemas ====================


class ProviderMetrics(BaseModel):
    """Metrics for a single LLM provider."""

    provider: LLMProviderType
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_latency_ms: float = 0.0
    avg_tokens: float = 0.0
    total_tokens: int = 0
    brands_mentioned: int = 0


class BrandMetrics(BaseModel):
    """Aggregated metrics for a brand across providers."""

    brand_name: str
    normalized_name: str
    total_mentions: int = 0
    mentions_by_provider: dict[str, int] = Field(default_factory=dict)
    presence_distribution: dict[str, int] = Field(default_factory=dict)
    belief_distribution: dict[str, int] = Field(default_factory=dict)
    avg_position: float = 0.0
    recommendation_rate: float = 0.0


class SimulationMetrics(BaseModel):
    """Comprehensive metrics for a simulation run."""

    simulation_id: uuid.UUID
    provider_metrics: list[ProviderMetrics] = Field(default_factory=list)
    brand_metrics: list[BrandMetrics] = Field(default_factory=list)
    intent_distribution: dict[str, int] = Field(default_factory=dict)
    total_unique_brands: int = 0


# ==================== Rate Limiting Schemas ====================


class RateLimitInfo(BaseModel):
    """Rate limit information for a provider or endpoint."""

    provider: str
    limit: int
    remaining: int
    reset_at: datetime
    is_limited: bool = False


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""

    requests_per_minute: int = Field(default=60)
    requests_per_hour: int = Field(default=1000)
    tokens_per_minute: int = Field(default=100000)
    concurrent_requests: int = Field(default=10)


# Update forward references
PromptQueueItem.model_rebuild()
