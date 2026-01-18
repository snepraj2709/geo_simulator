"""
Response Aggregator & Normalizer.

Aggregates and normalizes responses from multiple LLM providers,
providing unified access to response data for analysis.
Includes PostgreSQL storage integration for persisting metrics.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.logging import get_logger

from services.simulation.schemas import (
    BrandExtractionResult,
    BrandMetrics,
    LLMProviderType,
    NormalizedLLMResponse,
    ProviderMetrics,
    SimulationMetrics,
)

if TYPE_CHECKING:
    from services.simulation.components.analyzers import (
        EnhancedBrandExtraction,
        IntentAnalysisResult,
        PriorityAnalysis,
        FramingAnalysis,
    )

logger = get_logger(__name__)


@dataclass
class AggregatedPromptResponses:
    """Responses for a single prompt from all providers."""

    prompt_id: uuid.UUID
    prompt_text: str | None = None
    responses: dict[LLMProviderType, NormalizedLLMResponse] = field(default_factory=dict)
    brand_extractions: dict[LLMProviderType, BrandExtractionResult] = field(default_factory=dict)

    @property
    def provider_count(self) -> int:
        """Number of providers with responses."""
        return len(self.responses)

    @property
    def all_brands(self) -> set[str]:
        """Get all unique brands mentioned across all providers."""
        brands = set()
        for response in self.responses.values():
            brands.update(response.brands_mentioned)
        return brands

    def get_response(self, provider: LLMProviderType) -> NormalizedLLMResponse | None:
        """Get response for a specific provider."""
        return self.responses.get(provider)


class ResponseAggregator:
    """
    Aggregates LLM responses from multiple providers.

    Features:
    - Groups responses by prompt
    - Normalizes response formats
    - Calculates aggregate statistics
    - Provides unified access to response data

    Usage:
        aggregator = ResponseAggregator(simulation_id)
        aggregator.add_responses(responses)
        aggregator.add_brand_extractions(extractions)
        metrics = aggregator.get_metrics()
    """

    def __init__(self, simulation_id: uuid.UUID):
        """
        Initialize the aggregator.

        Args:
            simulation_id: UUID of the simulation run.
        """
        self.simulation_id = simulation_id

        # Storage
        self._responses: dict[uuid.UUID, AggregatedPromptResponses] = {}
        self._all_responses: list[NormalizedLLMResponse] = []

        # Metrics tracking
        self._provider_stats: dict[LLMProviderType, dict[str, Any]] = defaultdict(
            lambda: {
                "total_queries": 0,
                "successful_queries": 0,
                "failed_queries": 0,
                "total_tokens": 0,
                "total_latency_ms": 0,
                "brands_mentioned": 0,
            }
        )
        self._brand_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_mentions": 0,
                "mentions_by_provider": defaultdict(int),
                "presence_distribution": defaultdict(int),
                "belief_distribution": defaultdict(int),
                "positions": [],
            }
        )

    def add_response(self, response: NormalizedLLMResponse) -> None:
        """
        Add a single response.

        Args:
            response: Normalized LLM response to add.
        """
        self._all_responses.append(response)

        # Get or create aggregated responses for this prompt
        if response.prompt_id not in self._responses:
            self._responses[response.prompt_id] = AggregatedPromptResponses(
                prompt_id=response.prompt_id,
            )

        aggregated = self._responses[response.prompt_id]
        aggregated.responses[response.provider] = response

        # Update provider stats
        stats = self._provider_stats[response.provider]
        stats["total_queries"] += 1
        stats["successful_queries"] += 1
        stats["total_tokens"] += response.tokens_used
        stats["total_latency_ms"] += response.latency_ms
        stats["brands_mentioned"] += len(response.brands_mentioned)

        # Update brand stats
        for brand in response.brands_mentioned:
            normalized = brand.lower().strip()
            brand_stat = self._brand_stats[normalized]
            brand_stat["total_mentions"] += 1
            brand_stat["mentions_by_provider"][response.provider.value] += 1

        logger.debug(
            "Added response",
            prompt_id=str(response.prompt_id),
            provider=response.provider.value,
            brands=len(response.brands_mentioned),
        )

    def add_responses(self, responses: list[NormalizedLLMResponse]) -> None:
        """
        Add multiple responses.

        Args:
            responses: List of responses to add.
        """
        for response in responses:
            self.add_response(response)

    def add_brand_extraction(
        self,
        prompt_id: uuid.UUID,
        provider: LLMProviderType,
        extraction: BrandExtractionResult,
    ) -> None:
        """
        Add brand extraction result for a response.

        Args:
            prompt_id: Prompt UUID.
            provider: Provider the extraction is from.
            extraction: Brand extraction result.
        """
        if prompt_id not in self._responses:
            logger.warning(
                "Adding brand extraction for unknown prompt",
                prompt_id=str(prompt_id),
            )
            return

        aggregated = self._responses[prompt_id]
        aggregated.brand_extractions[provider] = extraction

        # Update detailed brand stats
        for brand in extraction.brands:
            normalized = brand.normalized_name
            brand_stat = self._brand_stats[normalized]
            brand_stat["presence_distribution"][brand.presence.value] += 1
            if brand.belief_sold:
                brand_stat["belief_distribution"][brand.belief_sold.value] += 1
            brand_stat["positions"].append(brand.position_rank)

    def get_prompt_responses(
        self,
        prompt_id: uuid.UUID,
    ) -> AggregatedPromptResponses | None:
        """
        Get all responses for a specific prompt.

        Args:
            prompt_id: Prompt UUID.

        Returns:
            Aggregated responses or None if not found.
        """
        return self._responses.get(prompt_id)

    def get_all_responses(self) -> list[NormalizedLLMResponse]:
        """Get all responses."""
        return self._all_responses.copy()

    def get_responses_by_provider(
        self,
        provider: LLMProviderType,
    ) -> list[NormalizedLLMResponse]:
        """
        Get all responses from a specific provider.

        Args:
            provider: LLM provider type.

        Returns:
            List of responses from the provider.
        """
        return [r for r in self._all_responses if r.provider == provider]

    def get_provider_metrics(self) -> list[ProviderMetrics]:
        """
        Get metrics for each provider.

        Returns:
            List of provider metrics.
        """
        metrics = []

        for provider, stats in self._provider_stats.items():
            total = stats["total_queries"]
            successful = stats["successful_queries"]

            metrics.append(
                ProviderMetrics(
                    provider=provider,
                    total_queries=total,
                    successful_queries=successful,
                    failed_queries=stats["failed_queries"],
                    avg_latency_ms=(
                        stats["total_latency_ms"] / successful if successful > 0 else 0
                    ),
                    avg_tokens=(
                        stats["total_tokens"] / successful if successful > 0 else 0
                    ),
                    total_tokens=stats["total_tokens"],
                    brands_mentioned=stats["brands_mentioned"],
                )
            )

        return metrics

    def get_brand_metrics(self) -> list[BrandMetrics]:
        """
        Get metrics for each discovered brand.

        Returns:
            List of brand metrics.
        """
        metrics = []

        for normalized_name, stats in self._brand_stats.items():
            total = stats["total_mentions"]
            positions = stats["positions"]

            # Calculate recommendation rate (presence = recommended)
            rec_count = stats["presence_distribution"].get("recommended", 0)
            rec_rate = rec_count / total if total > 0 else 0

            metrics.append(
                BrandMetrics(
                    brand_name=normalized_name.title(),
                    normalized_name=normalized_name,
                    total_mentions=total,
                    mentions_by_provider=dict(stats["mentions_by_provider"]),
                    presence_distribution=dict(stats["presence_distribution"]),
                    belief_distribution=dict(stats["belief_distribution"]),
                    avg_position=sum(positions) / len(positions) if positions else 0,
                    recommendation_rate=rec_rate,
                )
            )

        # Sort by total mentions descending
        metrics.sort(key=lambda m: m.total_mentions, reverse=True)

        return metrics

    def get_simulation_metrics(self) -> SimulationMetrics:
        """
        Get comprehensive simulation metrics.

        Returns:
            Simulation metrics object.
        """
        provider_metrics = self.get_provider_metrics()
        brand_metrics = self.get_brand_metrics()

        # Calculate intent distribution from brand extractions
        intent_distribution: dict[str, int] = defaultdict(int)
        for aggregated in self._responses.values():
            for extraction in aggregated.brand_extractions.values():
                if extraction.intent_ranking:
                    intent_distribution[extraction.intent_ranking.query_intent.value] += 1

        return SimulationMetrics(
            simulation_id=self.simulation_id,
            provider_metrics=provider_metrics,
            brand_metrics=brand_metrics,
            intent_distribution=dict(intent_distribution),
            total_unique_brands=len(self._brand_stats),
        )

    def get_statistics(self) -> dict[str, Any]:
        """
        Get summary statistics.

        Returns:
            Dictionary of statistics.
        """
        total_responses = len(self._all_responses)
        total_prompts = len(self._responses)
        total_brands = len(self._brand_stats)

        # Calculate totals per provider
        responses_by_provider = defaultdict(int)
        for response in self._all_responses:
            responses_by_provider[response.provider.value] += 1

        return {
            "simulation_id": str(self.simulation_id),
            "total_responses": total_responses,
            "total_prompts": total_prompts,
            "total_unique_brands": total_brands,
            "responses_by_provider": dict(responses_by_provider),
            "avg_brands_per_response": (
                sum(len(r.brands_mentioned) for r in self._all_responses) / total_responses
                if total_responses > 0
                else 0
            ),
        }

    def normalize_response_text(self, text: str) -> str:
        """
        Normalize response text for consistent processing.

        Args:
            text: Raw response text.

        Returns:
            Normalized text.
        """
        # Remove extra whitespace
        text = " ".join(text.split())

        # Ensure proper line breaks are preserved for structure
        # (this is a simple normalization; can be extended)

        return text.strip()

    def clear(self) -> None:
        """Clear all stored data."""
        self._responses.clear()
        self._all_responses.clear()
        self._provider_stats.clear()
        self._brand_stats.clear()

    async def store_aggregated_metrics(self, db: AsyncSession) -> uuid.UUID:
        """
        Store aggregated metrics to PostgreSQL.

        Args:
            db: Database session.

        Returns:
            UUID of the created AggregatedSimulationMetrics record.
        """
        from shared.models.aggregated_metrics import AggregatedSimulationMetrics

        metrics = self.get_simulation_metrics()
        stats = self.get_statistics()

        # Calculate average latency and tokens
        total_latency = 0
        total_tokens = 0
        count = 0

        for response in self._all_responses:
            total_latency += response.latency_ms
            total_tokens += response.tokens_used
            count += 1

        avg_latency = Decimal(total_latency / count) if count > 0 else Decimal(0)
        avg_tokens = Decimal(total_tokens / count) if count > 0 else Decimal(0)

        # Build provider metrics JSONB
        provider_metrics_json = {
            pm.provider.value: {
                "total_queries": pm.total_queries,
                "successful_queries": pm.successful_queries,
                "failed_queries": pm.failed_queries,
                "avg_latency_ms": pm.avg_latency_ms,
                "avg_tokens": pm.avg_tokens,
                "total_tokens": pm.total_tokens,
                "brands_mentioned": pm.brands_mentioned,
            }
            for pm in metrics.provider_metrics
        }

        # Build brand rankings JSONB
        brand_rankings_json = {
            bm.normalized_name: {
                "brand_name": bm.brand_name,
                "total_mentions": bm.total_mentions,
                "mentions_by_provider": bm.mentions_by_provider,
                "avg_position": bm.avg_position,
                "recommendation_rate": bm.recommendation_rate,
            }
            for bm in metrics.brand_metrics[:50]  # Top 50 brands
        }

        # Build belief distribution
        belief_dist = defaultdict(int)
        presence_dist = defaultdict(int)

        for bm in metrics.brand_metrics:
            for belief, count in bm.belief_distribution.items():
                belief_dist[belief] += count
            for presence, count in bm.presence_distribution.items():
                presence_dist[presence] += count

        aggregated = AggregatedSimulationMetrics(
            simulation_run_id=self.simulation_id,
            total_responses=stats["total_responses"],
            total_brands_found=stats["total_unique_brands"],
            total_prompts_processed=stats["total_prompts"],
            avg_latency_ms=avg_latency,
            avg_tokens_used=avg_tokens,
            total_tokens_used=total_tokens,
            provider_metrics=provider_metrics_json,
            intent_distribution=metrics.intent_distribution,
            funnel_distribution={},  # Populated by analyzer
            brand_rankings=brand_rankings_json,
            belief_distribution=dict(belief_dist),
            presence_distribution=dict(presence_dist),
            computed_at=datetime.utcnow(),
        )

        db.add(aggregated)
        await db.flush()

        logger.info(
            "Stored aggregated metrics",
            simulation_id=str(self.simulation_id),
            metrics_id=str(aggregated.id),
        )

        return aggregated.id

    async def store_brand_mention_analysis(
        self,
        db: AsyncSession,
        llm_response_id: uuid.UUID,
        brand_id: uuid.UUID,
        extraction: "EnhancedBrandExtraction",
        intent_result: "IntentAnalysisResult | None" = None,
        priority_analysis: "PriorityAnalysis | None" = None,
        framing_analysis: "FramingAnalysis | None" = None,
    ) -> uuid.UUID:
        """
        Store detailed brand mention analysis to PostgreSQL.

        Args:
            db: Database session.
            llm_response_id: UUID of the LLM response.
            brand_id: UUID of the brand.
            extraction: Enhanced brand extraction data.
            intent_result: Optional intent analysis result.
            priority_analysis: Optional priority analysis.
            framing_analysis: Optional framing analysis.

        Returns:
            UUID of the created BrandMentionAnalysis record.
        """
        from shared.models.aggregated_metrics import BrandMentionAnalysis

        analysis = BrandMentionAnalysis(
            llm_response_id=llm_response_id,
            brand_id=brand_id,
            extraction_method=extraction.extraction_method,
            position_in_response=extraction.position_in_response,
            mention_rank=extraction.mention_rank,
            mention_count=extraction.mention_count,
            context_snippet=extraction.context_snippet[:1000] if extraction.context_snippet else None,
            ner_entities=extraction.ner_entities if extraction.ner_entities else None,
        )

        # Add intent analysis if available
        if intent_result:
            analysis.intent_type = intent_result.primary_intent
            analysis.intent_confidence = Decimal(str(intent_result.confidence))

        # Add priority analysis if available
        if priority_analysis:
            analysis.priority_indicators = {
                "signals": [s.value for s in priority_analysis.priority_signals],
                "signal_scores": priority_analysis.signal_scores,
                "overall_score": priority_analysis.overall_priority_score,
            }

        # Add framing analysis if available
        if framing_analysis:
            analysis.contextual_framing = framing_analysis.framing_type.value
            analysis.framing_score = Decimal(str(framing_analysis.framing_score))

        db.add(analysis)
        await db.flush()

        return analysis.id

    async def store_intent_ranking_result(
        self,
        db: AsyncSession,
        llm_response_id: uuid.UUID,
        intent_result: "IntentAnalysisResult",
    ) -> uuid.UUID:
        """
        Store intent ranking result to PostgreSQL.

        Args:
            db: Database session.
            llm_response_id: UUID of the LLM response.
            intent_result: Intent analysis result.

        Returns:
            UUID of the created IntentRankingResult record.
        """
        from shared.models.aggregated_metrics import IntentRankingResult

        result = IntentRankingResult(
            llm_response_id=llm_response_id,
            primary_intent=intent_result.primary_intent,
            secondary_intent=intent_result.secondary_intent,
            intent_confidence=Decimal(str(intent_result.confidence)),
            commercial_score=Decimal(str(intent_result.intent_scores.get("Commercial", 0))),
            informational_score=Decimal(str(intent_result.intent_scores.get("Informational", 0))),
            transactional_score=Decimal(str(intent_result.intent_scores.get("Transactional", 0))),
            navigational_score=Decimal(str(intent_result.intent_scores.get("Navigational", 0))),
            buying_signals=intent_result.buying_signals if intent_result.buying_signals else None,
            trust_indicators=intent_result.trust_indicators if intent_result.trust_indicators else None,
            funnel_stage=intent_result.funnel_stage,
            query_type=intent_result.query_type,
        )

        db.add(result)
        await db.flush()

        return result.id


class ResponseNormalizer:
    """
    Normalizes individual LLM responses for consistent processing.

    Handles provider-specific formatting differences and extracts
    structured data from responses.
    """

    @staticmethod
    def normalize(response: NormalizedLLMResponse) -> NormalizedLLMResponse:
        """
        Normalize a response.

        Args:
            response: Response to normalize.

        Returns:
            Normalized response.
        """
        # Normalize response text
        normalized_text = ResponseNormalizer._normalize_text(response.response_text)

        return NormalizedLLMResponse(
            id=response.id,
            simulation_run_id=response.simulation_run_id,
            prompt_id=response.prompt_id,
            provider=response.provider,
            model=response.model,
            response_text=normalized_text,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
            brands_mentioned=response.brands_mentioned,
            created_at=response.created_at,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize response text."""
        if not text:
            return ""

        # Remove leading/trailing whitespace
        text = text.strip()

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")

        return text

    @staticmethod
    def extract_sections(text: str) -> dict[str, str]:
        """
        Extract sections from structured responses.

        Args:
            text: Response text.

        Returns:
            Dict mapping section headers to content.
        """
        sections: dict[str, str] = {}
        current_section = "main"
        current_content: list[str] = []

        lines = text.split("\n")
        for line in lines:
            # Check for section headers (##, ###, etc.)
            stripped = line.strip()
            if stripped.startswith("#"):
                # Save current section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = stripped.lstrip("#").strip().lower()
                current_content = []
            else:
                current_content.append(line)

        # Save final section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections
