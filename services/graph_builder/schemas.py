"""
Pydantic schemas for Knowledge Graph Builder.

Defines all Node and Edge types for the Neo4j knowledge graph.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class BeliefTypeEnum(str, Enum):
    """Types of beliefs that LLMs can install about brands."""

    TRUTH = "truth"  # epistemic clarity, neutrality
    SUPERIORITY = "superiority"  # better than alternatives
    OUTCOME = "outcome"  # ROI, performance, results
    TRANSACTION = "transaction"  # buy now, act
    IDENTITY = "identity"  # people like you use this
    SOCIAL_PROOF = "social_proof"  # others chose this


class PresenceStateEnum(str, Enum):
    """Brand presence states in LLM responses."""

    IGNORED = "ignored"
    MENTIONED = "mentioned"
    TRUSTED = "trusted"
    RECOMMENDED = "recommended"
    COMPARED = "compared"


class IntentTypeEnum(str, Enum):
    """Types of user intent."""

    INFORMATIONAL = "informational"
    EVALUATION = "evaluation"
    DECISION = "decision"


class FunnelStageEnum(str, Enum):
    """Stages in the buying funnel."""

    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    PURCHASE = "purchase"


class RelationshipTypeEnum(str, Enum):
    """Types of competitive relationships."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    SUBSTITUTE = "substitute"


# =============================================================================
# NODE SCHEMAS
# =============================================================================


class BrandNode(BaseModel):
    """Brand node in the knowledge graph."""

    id: str = Field(..., description="UUID from PostgreSQL")
    name: str = Field(..., description="Brand name")
    normalized_name: str = Field(..., description="Lowercase, trimmed name")
    domain: str | None = Field(None, description="Brand's domain")
    industry: str | None = Field(None, description="Brand's industry")
    is_tracked: bool = Field(False, description="Whether this is the user's brand")


class ICPNode(BaseModel):
    """Ideal Customer Profile node."""

    id: str = Field(..., description="UUID")
    name: str = Field(..., description="ICP name")
    website_id: str = Field(..., description="Associated website UUID")
    demographics: dict[str, Any] = Field(default_factory=dict, description="Demographics data")
    pain_points: list[str] = Field(default_factory=list, description="List of pain points")
    goals: list[str] = Field(default_factory=list, description="List of goals")


class IntentNode(BaseModel):
    """User intent node derived from prompts."""

    id: str = Field(..., description="UUID")
    prompt_id: str = Field(..., description="Associated prompt UUID")
    intent_type: IntentTypeEnum = Field(..., description="Type of intent")
    funnel_stage: FunnelStageEnum = Field(..., description="Funnel stage")
    buying_signal: float = Field(..., ge=0.0, le=1.0, description="Buying signal score")
    trust_need: float = Field(..., ge=0.0, le=1.0, description="Trust need score")
    query_text: str | None = Field(None, description="Original query text")


class ConcernNode(BaseModel):
    """Concern/Pain Point node."""

    id: str = Field(..., description="UUID")
    description: str = Field(..., description="Concern description")
    category: str | None = Field(None, description="Category of concern")


class BeliefTypeNode(BaseModel):
    """Belief type node."""

    type: BeliefTypeEnum = Field(..., description="Type of belief")


class LLMProviderNode(BaseModel):
    """LLM Provider node."""

    name: str = Field(..., description="Provider name (openai, google, anthropic, perplexity)")
    model: str = Field(..., description="Model identifier")


class ConversationNode(BaseModel):
    """Conversation node."""

    id: str = Field(..., description="UUID")
    topic: str = Field(..., description="Conversation topic")
    context: str | None = Field(None, description="Situational context")


# =============================================================================
# EDGE SCHEMAS
# =============================================================================


class CoMentionedEdge(BaseModel):
    """CO_MENTIONED relationship between brands."""

    source_brand_id: str = Field(..., description="Source brand UUID")
    target_brand_id: str = Field(..., description="Target brand UUID")
    count: int = Field(1, description="Number of co-occurrences")
    avg_position_delta: float | None = Field(None, description="Average position difference")
    llm_provider: str | None = Field(None, description="LLM provider name")


class CompetesWithEdge(BaseModel):
    """COMPETES_WITH relationship between brands."""

    source_brand_id: str = Field(..., description="Primary brand UUID")
    target_brand_id: str = Field(..., description="Competitor brand UUID")
    relationship_type: RelationshipTypeEnum = Field(..., description="Type of competition")


class HasConcernEdge(BaseModel):
    """HAS_CONCERN relationship from ICP to Concern."""

    icp_id: str = Field(..., description="ICP UUID")
    concern_id: str = Field(..., description="Concern UUID")
    priority: int = Field(1, ge=1, description="Priority ranking")


class InitiatesEdge(BaseModel):
    """INITIATES relationship from ICP to Conversation."""

    icp_id: str = Field(..., description="ICP UUID")
    conversation_id: str = Field(..., description="Conversation UUID")


class TriggersEdge(BaseModel):
    """TRIGGERS relationship from Concern to Intent."""

    concern_id: str = Field(..., description="Concern UUID")
    intent_id: str = Field(..., description="Intent UUID")


class ContainsEdge(BaseModel):
    """CONTAINS relationship from Conversation to Intent."""

    conversation_id: str = Field(..., description="Conversation UUID")
    intent_id: str = Field(..., description="Intent UUID")


class RanksForEdge(BaseModel):
    """RANKS_FOR relationship from Brand to Intent."""

    brand_id: str = Field(..., description="Brand UUID")
    intent_id: str = Field(..., description="Intent UUID")
    position: int = Field(..., ge=1, description="Position rank")
    presence: PresenceStateEnum = Field(..., description="Presence state")
    llm_provider: str = Field(..., description="LLM provider name")
    count: int = Field(1, description="Number of occurrences")


class InstallsBeliefEdge(BaseModel):
    """INSTALLS_BELIEF relationship from Brand to BeliefType."""

    brand_id: str = Field(..., description="Brand UUID")
    belief_type: BeliefTypeEnum = Field(..., description="Type of belief installed")
    intent_id: str | None = Field(None, description="Associated intent UUID")
    llm_provider: str | None = Field(None, description="LLM provider name")
    count: int = Field(1, description="Number of occurrences")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")


class RecommendsEdge(BaseModel):
    """RECOMMENDS relationship from LLMProvider to Brand."""

    llm_provider: str = Field(..., description="LLM provider name")
    llm_model: str = Field(..., description="LLM model")
    brand_id: str = Field(..., description="Brand UUID")
    intent_id: str | None = Field(None, description="Associated intent UUID")
    position: int = Field(..., ge=1, description="Position in response")
    belief_type: BeliefTypeEnum | None = Field(None, description="Belief type conveyed")


class IgnoresEdge(BaseModel):
    """IGNORES relationship from LLMProvider to Brand."""

    llm_provider: str = Field(..., description="LLM provider name")
    llm_model: str = Field(..., description="LLM model")
    brand_id: str = Field(..., description="Brand UUID")
    intent_id: str | None = Field(None, description="Associated intent UUID")
    competitor_mentioned: str | None = Field(None, description="Competitor that was mentioned instead")


# =============================================================================
# API REQUEST/RESPONSE SCHEMAS
# =============================================================================


class GraphBuildRequest(BaseModel):
    """Request to build graph from simulation data."""

    website_id: str = Field(..., description="Website UUID")
    simulation_run_id: str | None = Field(None, description="Specific simulation run UUID")
    incremental: bool = Field(True, description="Whether to incrementally update")


class GraphBuildResponse(BaseModel):
    """Response from graph build operation."""

    success: bool = Field(..., description="Whether build succeeded")
    nodes_created: int = Field(0, description="Number of nodes created")
    edges_created: int = Field(0, description="Number of edges created")
    nodes_updated: int = Field(0, description="Number of nodes updated")
    edges_updated: int = Field(0, description="Number of edges updated")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    build_duration_ms: int | None = Field(None, description="Build duration in milliseconds")


class BeliefMapRequest(BaseModel):
    """Request for belief map data."""

    brand_name: str = Field(..., description="Brand name to query")
    llm_provider: str | None = Field(None, description="Filter by LLM provider")
    intent_type: IntentTypeEnum | None = Field(None, description="Filter by intent type")


class BeliefMapResponse(BaseModel):
    """Response containing belief map data."""

    brand_name: str = Field(..., description="Brand name")
    beliefs: list[dict[str, Any]] = Field(default_factory=list, description="Belief type distribution")
    total_occurrences: int = Field(0, description="Total occurrences")


class CoMentionRequest(BaseModel):
    """Request for co-mention data."""

    brand_name: str = Field(..., description="Brand name to query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    llm_provider: str | None = Field(None, description="Filter by LLM provider")


class CoMentionResponse(BaseModel):
    """Response containing co-mention data."""

    brand_name: str = Field(..., description="Source brand")
    co_mentions: list[dict[str, Any]] = Field(default_factory=list, description="Co-mentioned brands")


class ICPJourneyRequest(BaseModel):
    """Request for ICP journey data."""

    icp_id: str = Field(..., description="ICP UUID")
    include_brands: bool = Field(True, description="Include brand recommendations")


class ICPJourneyResponse(BaseModel):
    """Response containing ICP journey data."""

    icp_id: str = Field(..., description="ICP UUID")
    icp_name: str = Field(..., description="ICP name")
    concerns: list[dict[str, Any]] = Field(default_factory=list, description="ICP concerns")
    intents: list[dict[str, Any]] = Field(default_factory=list, description="Triggered intents")
    brand_recommendations: list[dict[str, Any]] = Field(default_factory=list, description="Brand recommendations")


class SubstitutionPatternRequest(BaseModel):
    """Request for substitution pattern data."""

    brand_name: str = Field(..., description="Missing brand name")
    llm_provider: str | None = Field(None, description="Filter by LLM provider")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")


class SubstitutionPatternResponse(BaseModel):
    """Response containing substitution patterns."""

    missing_brand: str = Field(..., description="Brand that was ignored")
    substitutes: list[dict[str, Any]] = Field(default_factory=list, description="Substitute brands")


# =============================================================================
# BATCH OPERATION SCHEMAS
# =============================================================================


class BatchNodeCreate(BaseModel):
    """Batch node creation request."""

    brands: list[BrandNode] = Field(default_factory=list)
    icps: list[ICPNode] = Field(default_factory=list)
    intents: list[IntentNode] = Field(default_factory=list)
    concerns: list[ConcernNode] = Field(default_factory=list)
    conversations: list[ConversationNode] = Field(default_factory=list)


class BatchEdgeCreate(BaseModel):
    """Batch edge creation request."""

    co_mentions: list[CoMentionedEdge] = Field(default_factory=list)
    competes_with: list[CompetesWithEdge] = Field(default_factory=list)
    has_concerns: list[HasConcernEdge] = Field(default_factory=list)
    initiates: list[InitiatesEdge] = Field(default_factory=list)
    triggers: list[TriggersEdge] = Field(default_factory=list)
    contains: list[ContainsEdge] = Field(default_factory=list)
    ranks_for: list[RanksForEdge] = Field(default_factory=list)
    installs_beliefs: list[InstallsBeliefEdge] = Field(default_factory=list)
    recommends: list[RecommendsEdge] = Field(default_factory=list)
    ignores: list[IgnoresEdge] = Field(default_factory=list)


class BatchOperationResult(BaseModel):
    """Result of a batch operation."""

    success: bool = Field(..., description="Whether operation succeeded")
    created: int = Field(0, description="Number of items created")
    updated: int = Field(0, description="Number of items updated")
    failed: int = Field(0, description="Number of items that failed")
    errors: list[str] = Field(default_factory=list, description="Error messages")
