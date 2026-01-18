"""Add aggregated simulation metrics tables.

Revision ID: 002
Revises: 001
Create Date: 2026-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== Aggregated Simulation Metrics ====================
    op.create_table(
        "aggregated_simulation_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "simulation_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Summary counts
        sa.Column("total_responses", sa.Integer, server_default="0"),
        sa.Column("total_brands_found", sa.Integer, server_default="0"),
        sa.Column("total_prompts_processed", sa.Integer, server_default="0"),
        # Performance metrics
        sa.Column("avg_latency_ms", sa.Numeric(10, 2)),
        sa.Column("avg_tokens_used", sa.Numeric(10, 2)),
        sa.Column("total_tokens_used", sa.Integer, server_default="0"),
        # JSONB aggregations
        sa.Column("provider_metrics", postgresql.JSONB),
        sa.Column("intent_distribution", postgresql.JSONB),
        sa.Column("funnel_distribution", postgresql.JSONB),
        sa.Column("brand_rankings", postgresql.JSONB),
        sa.Column("belief_distribution", postgresql.JSONB),
        sa.Column("presence_distribution", postgresql.JSONB),
        # Timestamps
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_aggregated_metrics_simulation_run_id",
        "aggregated_simulation_metrics",
        ["simulation_run_id"],
    )
    op.create_index(
        "idx_aggregated_metrics_computed",
        "aggregated_simulation_metrics",
        ["computed_at"],
    )

    # ==================== Brand Mention Analysis ====================
    op.create_table(
        "brand_mention_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "llm_response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("llm_responses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Extraction metadata
        sa.Column("extraction_method", sa.String(50), server_default="combined"),
        # Position analysis
        sa.Column("position_in_response", sa.Integer),
        sa.Column("mention_rank", sa.Integer),
        sa.Column("mention_count", sa.Integer, server_default="1"),
        # Context analysis
        sa.Column("context_snippet", sa.Text),
        sa.Column("contextual_framing", sa.String(50)),
        sa.Column("framing_score", sa.Numeric(4, 3)),
        # Intent analysis
        sa.Column("intent_type", sa.String(50)),
        sa.Column("intent_confidence", sa.Numeric(4, 3)),
        # JSONB for complex data
        sa.Column("priority_indicators", postgresql.JSONB),
        sa.Column("ner_entities", postgresql.JSONB),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_brand_mention_llm_response_id",
        "brand_mention_analyses",
        ["llm_response_id"],
    )
    op.create_index(
        "ix_brand_mention_brand_id",
        "brand_mention_analyses",
        ["brand_id"],
    )
    op.create_index(
        "idx_brand_mention_response_brand",
        "brand_mention_analyses",
        ["llm_response_id", "brand_id"],
    )
    op.create_index(
        "idx_brand_mention_intent",
        "brand_mention_analyses",
        ["intent_type"],
    )
    op.create_index(
        "idx_brand_mention_framing",
        "brand_mention_analyses",
        ["contextual_framing"],
    )

    # ==================== Intent Ranking Results ====================
    op.create_table(
        "intent_ranking_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "llm_response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("llm_responses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Primary classification
        sa.Column("primary_intent", sa.String(50), nullable=False),
        sa.Column("secondary_intent", sa.String(50)),
        sa.Column("intent_confidence", sa.Numeric(4, 3), server_default="0"),
        # Intent scores
        sa.Column("commercial_score", sa.Numeric(4, 3), server_default="0"),
        sa.Column("informational_score", sa.Numeric(4, 3), server_default="0"),
        sa.Column("transactional_score", sa.Numeric(4, 3), server_default="0"),
        sa.Column("navigational_score", sa.Numeric(4, 3), server_default="0"),
        # JSONB for signals
        sa.Column("buying_signals", postgresql.JSONB),
        sa.Column("trust_indicators", postgresql.JSONB),
        # Classification
        sa.Column("funnel_stage", sa.String(50)),
        sa.Column("query_type", sa.String(100)),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index(
        "ix_intent_ranking_llm_response_id",
        "intent_ranking_results",
        ["llm_response_id"],
    )
    op.create_index(
        "ix_intent_ranking_primary_intent",
        "intent_ranking_results",
        ["primary_intent"],
    )
    op.create_index(
        "idx_intent_ranking_funnel",
        "intent_ranking_results",
        ["funnel_stage"],
    )


def downgrade() -> None:
    op.drop_table("intent_ranking_results")
    op.drop_table("brand_mention_analyses")
    op.drop_table("aggregated_simulation_metrics")
