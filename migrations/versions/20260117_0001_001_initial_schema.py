"""Initial schema with all tables.

Revision ID: 001
Revises:
Create Date: 2026-01-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==================== Organizations ====================
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan_type", sa.String(50), server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # ==================== Users ====================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ==================== Websites ====================
    op.create_table(
        "websites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True)),
        sa.Column("last_hard_scrape_at", sa.DateTime(timezone=True)),
        sa.Column("scrape_depth", sa.Integer, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("organization_id", "domain", name="uq_websites_org_domain"),
    )
    op.create_index("ix_websites_organization_id", "websites", ["organization_id"])
    op.create_index("ix_websites_domain", "websites", ["domain"])
    op.create_index("ix_websites_status", "websites", ["status"])

    # ==================== Scraped Pages ====================
    op.create_table(
        "scraped_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512)),
        sa.Column("meta_description", sa.Text),
        sa.Column("content_text", sa.Text),
        sa.Column("content_html_path", sa.String(512)),
        sa.Column("word_count", sa.Integer),
        sa.Column("page_type", sa.String(50)),
        sa.Column("http_status", sa.Integer),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("website_id", "url_hash", name="uq_scraped_pages_website_url"),
    )
    op.create_index("ix_scraped_pages_website_id", "scraped_pages", ["website_id"])
    op.create_index("ix_scraped_pages_url_hash", "scraped_pages", ["url_hash"])
    op.create_index("ix_scraped_pages_page_type", "scraped_pages", ["page_type"])

    # ==================== Website Analysis ====================
    op.create_table(
        "website_analysis",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("industry", sa.String(255)),
        sa.Column("business_model", sa.String(100)),
        sa.Column("primary_offerings", postgresql.JSONB),
        sa.Column("value_propositions", postgresql.JSONB),
        sa.Column("target_markets", postgresql.JSONB),
        sa.Column("competitors_mentioned", postgresql.JSONB),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_website_analysis_website_id", "website_analysis", ["website_id"])

    # ==================== ICPs ====================
    op.create_table(
        "icps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column("demographics", postgresql.JSONB, nullable=False),
        sa.Column("professional_profile", postgresql.JSONB, nullable=False),
        sa.Column("pain_points", postgresql.JSONB, nullable=False),
        sa.Column("goals", postgresql.JSONB, nullable=False),
        sa.Column("motivations", postgresql.JSONB, nullable=False),
        sa.Column("objections", postgresql.JSONB),
        sa.Column("decision_factors", postgresql.JSONB),
        sa.Column("information_sources", postgresql.JSONB),
        sa.Column("buying_journey_stage", sa.String(50)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("website_id", "sequence_number", name="uq_icps_website_sequence"),
    )
    op.create_index("ix_icps_website_id", "icps", ["website_id"])
    op.create_index(
        "idx_icps_active",
        "icps",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # ==================== Conversation Sequences ====================
    op.create_table(
        "conversation_sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icp_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("icps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("context", sa.Text),
        sa.Column("expected_outcome", sa.Text),
        sa.Column("is_core_conversation", sa.Boolean, server_default="false"),
        sa.Column("sequence_number", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("icp_id", "sequence_number", name="uq_conversations_icp_sequence"),
    )
    op.create_index("ix_conversation_sequences_website_id", "conversation_sequences", ["website_id"])
    op.create_index("ix_conversation_sequences_icp_id", "conversation_sequences", ["icp_id"])
    op.create_index(
        "idx_conversations_core",
        "conversation_sequences",
        ["is_core_conversation"],
        postgresql_where=sa.text("is_core_conversation = true"),
    )

    # ==================== Prompts ====================
    op.create_table(
        "prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversation_sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_text", sa.Text, nullable=False),
        sa.Column("prompt_type", sa.String(50), nullable=False, server_default="primary"),
        sa.Column("sequence_order", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_prompts_conversation_id", "prompts", ["conversation_id"])
    op.create_index("ix_prompts_prompt_type", "prompts", ["prompt_type"])

    # ==================== Prompt Classifications ====================
    op.create_table(
        "prompt_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompts.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("intent_type", sa.String(50), nullable=False),
        sa.Column("funnel_stage", sa.String(50), nullable=False),
        sa.Column("buying_signal", sa.Numeric(3, 2), nullable=False),
        sa.Column("trust_need", sa.Numeric(3, 2), nullable=False),
        sa.Column("query_intent", sa.String(50)),
        sa.Column("confidence_score", sa.Numeric(3, 2)),
        sa.Column("classified_at", sa.DateTime(timezone=True)),
        sa.Column("classifier_version", sa.String(50)),
    )
    op.create_index("ix_prompt_classifications_prompt_id", "prompt_classifications", ["prompt_id"])
    op.create_index("ix_prompt_classifications_intent_type", "prompt_classifications", ["intent_type"])
    op.create_index("ix_prompt_classifications_funnel_stage", "prompt_classifications", ["funnel_stage"])

    # ==================== Simulation Runs ====================
    op.create_table(
        "simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("total_prompts", sa.Integer),
        sa.Column("completed_prompts", sa.Integer, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_simulation_runs_website_id", "simulation_runs", ["website_id"])
    op.create_index("ix_simulation_runs_status", "simulation_runs", ["status"])

    # ==================== LLM Responses ====================
    op.create_table(
        "llm_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("llm_provider", sa.String(50), nullable=False),
        sa.Column("llm_model", sa.String(100), nullable=False),
        sa.Column("response_text", sa.Text, nullable=False),
        sa.Column("response_tokens", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("brands_mentioned", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("simulation_run_id", "prompt_id", "llm_provider", name="uq_llm_responses_run_prompt_provider"),
    )
    op.create_index("ix_llm_responses_simulation_run_id", "llm_responses", ["simulation_run_id"])
    op.create_index("ix_llm_responses_prompt_id", "llm_responses", ["prompt_id"])
    op.create_index("ix_llm_responses_llm_provider", "llm_responses", ["llm_provider"])

    # ==================== Brands ====================
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), unique=True, nullable=False),
        sa.Column("domain", sa.String(255)),
        sa.Column("industry", sa.String(255)),
        sa.Column("is_tracked", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_brands_normalized_name", "brands", ["normalized_name"])
    op.create_index(
        "idx_brands_tracked",
        "brands",
        ["is_tracked"],
        postgresql_where=sa.text("is_tracked = true"),
    )

    # ==================== LLM Brand States ====================
    op.create_table(
        "llm_brand_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("llm_response_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("presence", sa.String(50), nullable=False),
        sa.Column("position_rank", sa.Integer),
        sa.Column("belief_sold", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("llm_response_id", "brand_id", name="uq_llm_brand_states_response_brand"),
    )
    op.create_index("ix_llm_brand_states_llm_response_id", "llm_brand_states", ["llm_response_id"])
    op.create_index("ix_llm_brand_states_brand_id", "llm_brand_states", ["brand_id"])
    op.create_index("ix_llm_brand_states_presence", "llm_brand_states", ["presence"])
    op.create_index("ix_llm_brand_states_belief_sold", "llm_brand_states", ["belief_sold"])

    # ==================== LLM Answer Belief Maps ====================
    op.create_table(
        "llm_answer_belief_maps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("llm_response_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_classification_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_classifications.id", ondelete="SET NULL")),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("intent_type", sa.String(50)),
        sa.Column("funnel_stage", sa.String(50)),
        sa.Column("buying_signal", sa.Numeric(3, 2)),
        sa.Column("trust_need", sa.Numeric(3, 2)),
        sa.Column("presence", sa.String(50)),
        sa.Column("position_rank", sa.Integer),
        sa.Column("belief_sold", sa.String(50)),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_llm_answer_belief_maps_llm_response_id", "llm_answer_belief_maps", ["llm_response_id"])
    op.create_index("ix_llm_answer_belief_maps_brand_id", "llm_answer_belief_maps", ["brand_id"])
    op.create_index("ix_llm_answer_belief_maps_intent_type", "llm_answer_belief_maps", ["intent_type"])
    op.create_index("ix_llm_answer_belief_maps_llm_provider", "llm_answer_belief_maps", ["llm_provider"])

    # ==================== Competitor Relationships ====================
    op.create_table(
        "competitor_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("primary_brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("competitor_brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("website_id", "primary_brand_id", "competitor_brand_id", name="uq_competitor_relationships_brands"),
    )
    op.create_index("ix_competitor_relationships_website_id", "competitor_relationships", ["website_id"])
    op.create_index("ix_competitor_relationships_primary_brand_id", "competitor_relationships", ["primary_brand_id"])

    # ==================== Share of Voice ====================
    op.create_table(
        "share_of_voice",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("llm_provider", sa.String(50), nullable=False),
        sa.Column("mention_count", sa.Integer, server_default="0"),
        sa.Column("recommendation_count", sa.Integer, server_default="0"),
        sa.Column("first_position_count", sa.Integer, server_default="0"),
        sa.Column("total_responses", sa.Integer, server_default="0"),
        sa.Column("visibility_score", sa.Numeric(5, 2)),
        sa.Column("trust_score", sa.Numeric(5, 2)),
        sa.Column("recommendation_rate", sa.Numeric(5, 2)),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("website_id", "brand_id", "llm_provider", "period_start", "period_end", name="uq_share_of_voice_period"),
    )
    op.create_index("ix_share_of_voice_website_id", "share_of_voice", ["website_id"])
    op.create_index("ix_share_of_voice_brand_id", "share_of_voice", ["brand_id"])
    op.create_index("ix_share_of_voice_period_start", "share_of_voice", ["period_start"])

    # ==================== Substitution Patterns ====================
    op.create_table(
        "substitution_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("websites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("missing_brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("substitute_brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False),
        sa.Column("occurrence_count", sa.Integer, server_default="1"),
        sa.Column("avg_position", sa.Numeric(3, 1)),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("period_start", sa.Date),
        sa.Column("period_end", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_substitution_patterns_website_id", "substitution_patterns", ["website_id"])
    op.create_index("ix_substitution_patterns_missing_brand_id", "substitution_patterns", ["missing_brand_id"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("substitution_patterns")
    op.drop_table("share_of_voice")
    op.drop_table("competitor_relationships")
    op.drop_table("llm_answer_belief_maps")
    op.drop_table("llm_brand_states")
    op.drop_table("brands")
    op.drop_table("llm_responses")
    op.drop_table("simulation_runs")
    op.drop_table("prompt_classifications")
    op.drop_table("prompts")
    op.drop_table("conversation_sequences")
    op.drop_table("icps")
    op.drop_table("website_analysis")
    op.drop_table("scraped_pages")
    op.drop_table("websites")
    op.drop_table("users")
    op.drop_table("organizations")
