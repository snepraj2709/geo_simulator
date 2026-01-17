"""
Simulation and LLM Response models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin
from shared.models.enums import SimulationStatus

if TYPE_CHECKING:
    from shared.models.website import Website
    from shared.models.conversation import Prompt
    from shared.models.brand import LLMBrandState


class SimulationRun(Base, UUIDMixin, TimestampMixin):
    """Simulation run model."""

    __tablename__ = "simulation_runs"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=SimulationStatus.PENDING.value,
        index=True,
    )
    total_prompts: Mapped[int | None] = mapped_column(Integer)
    completed_prompts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="simulation_runs",
    )
    responses: Mapped[list["LLMResponse"]] = relationship(
        "LLMResponse",
        back_populates="simulation_run",
        cascade="all, delete-orphan",
    )


class LLMResponse(Base, UUIDMixin, TimestampMixin):
    """LLM response model."""

    __tablename__ = "llm_responses"

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)

    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)

    brands_mentioned: Mapped[list[str] | None] = mapped_column(JSONB)

    # Relationships
    simulation_run: Mapped["SimulationRun"] = relationship(
        "SimulationRun",
        back_populates="responses",
    )
    prompt: Mapped["Prompt"] = relationship(
        "Prompt",
        back_populates="llm_responses",
    )
    brand_states: Mapped[list["LLMBrandState"]] = relationship(
        "LLMBrandState",
        back_populates="llm_response",
        cascade="all, delete-orphan",
    )
