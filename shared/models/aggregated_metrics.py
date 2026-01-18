"""
Aggregated Simulation Metrics models.

Stores pre-computed metrics and analysis results from simulation runs
for efficient querying and dashboard performance.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.simulation import SimulationRun
    from shared.models.brand import Brand


class AggregatedSimulationMetrics(Base, UUIDMixin, TimestampMixin):
    """
    Aggregated metrics for a simulation run.

    Pre-computes and stores summary statistics from simulation responses
    for efficient dashboard queries.

    Attributes:
        simulation_run_id: Parent simulation run
        total_responses: Total LLM responses collected
        total_brands_found: Total unique brands discovered
        total_prompts_processed: Number of prompts processed
        avg_latency_ms: Average response latency
        avg_tokens_used: Average tokens per response
        provider_metrics: JSONB of per-provider statistics
        intent_distribution: JSONB of intent type counts
        funnel_distribution: JSONB of funnel stage counts
        brand_rankings: JSONB of brand ranking data
        computed_at: When metrics were computed
    """

    __tablename__ = "aggregated_simulation_metrics"

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Summary counts
    total_responses: Mapped[int] = mapped_column(Integer, default=0)
    total_brands_found: Mapped[int] = mapped_column(Integer, default=0)
    total_prompts_processed: Mapped[int] = mapped_column(Integer, default=0)

    # Performance metrics
    avg_latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    avg_tokens_used: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    # JSONB aggregations
    provider_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    intent_distribution: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    funnel_distribution: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    brand_rankings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    belief_distribution: Mapped[dict[str, int] | None] = mapped_column(JSONB)
    presence_distribution: Mapped[dict[str, int] | None] = mapped_column(JSONB)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    # Relationships
    simulation_run: Mapped["SimulationRun"] = relationship(
        "SimulationRun",
        back_populates="aggregated_metrics",
    )

    __table_args__ = (
        Index("idx_aggregated_metrics_computed", "computed_at"),
    )


class BrandMentionAnalysis(Base, UUIDMixin, TimestampMixin):
    """
    Detailed brand mention analysis per response.

    Stores extracted brand mentions with NER data, position analysis,
    contextual framing, and intent rankings.

    Attributes:
        llm_response_id: Source LLM response
        brand_id: The brand being analyzed
        extraction_method: regex, ner, llm, or combined
        position_in_response: Character position of first mention
        mention_rank: Order of mention (1 = first mentioned)
        mention_count: Number of times brand appears
        context_snippet: Text surrounding brand mention
        contextual_framing: Framing type (positive, neutral, negative)
        framing_score: Sentiment score (-1 to 1)
        intent_type: Detected query intent
        intent_confidence: Confidence of intent detection
        priority_indicators: JSONB of priority signals detected
        ner_entities: JSONB of NER-extracted related entities
    """

    __tablename__ = "brand_mention_analyses"

    llm_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_responses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Extraction metadata
    extraction_method: Mapped[str] = mapped_column(
        String(50),
        default="combined",
    )

    # Position analysis
    position_in_response: Mapped[int | None] = mapped_column(Integer)
    mention_rank: Mapped[int | None] = mapped_column(Integer)
    mention_count: Mapped[int] = mapped_column(Integer, default=1)

    # Context analysis
    context_snippet: Mapped[str | None] = mapped_column(Text)
    contextual_framing: Mapped[str | None] = mapped_column(String(50))
    framing_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))

    # Intent analysis
    intent_type: Mapped[str | None] = mapped_column(String(50), index=True)
    intent_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))

    # JSONB for complex data
    priority_indicators: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ner_entities: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Relationships
    brand: Mapped["Brand"] = relationship("Brand")

    __table_args__ = (
        Index("idx_brand_mention_response_brand", "llm_response_id", "brand_id"),
        Index("idx_brand_mention_intent", "intent_type"),
        Index("idx_brand_mention_framing", "contextual_framing"),
    )


class IntentRankingResult(Base, UUIDMixin, TimestampMixin):
    """
    Intent ranking analysis for a response.

    Stores detailed intent analysis including commercial signals,
    buying intent, and trust indicators.

    Attributes:
        llm_response_id: Source LLM response
        primary_intent: Main detected intent
        secondary_intent: Secondary intent if mixed
        intent_confidence: Confidence score
        commercial_score: Commercial intent strength (0-1)
        informational_score: Informational intent strength (0-1)
        transactional_score: Transactional intent strength (0-1)
        navigational_score: Navigational intent strength (0-1)
        buying_signals: JSONB of detected buying signals
        trust_indicators: JSONB of trust-building indicators
        funnel_stage: Detected funnel stage
        query_type: Type of query analyzed
    """

    __tablename__ = "intent_ranking_results"

    llm_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_responses.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Primary classification
    primary_intent: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    secondary_intent: Mapped[str | None] = mapped_column(String(50))
    intent_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0.0)

    # Intent scores (all sum to ~1.0)
    commercial_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0.0)
    informational_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0.0)
    transactional_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0.0)
    navigational_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0.0)

    # JSONB for signals
    buying_signals: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    trust_indicators: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Classification
    funnel_stage: Mapped[str | None] = mapped_column(String(50))
    query_type: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (
        Index("idx_intent_ranking_funnel", "funnel_stage"),
    )
