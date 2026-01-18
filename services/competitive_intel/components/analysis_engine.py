"""
Competitive Analysis Engine.

Implements core analysis algorithms:
- Share-of-voice calculation by LLM provider
- Substitution pattern detection
- Competitive gap identification
- Opportunity scoring
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
import uuid

from shared.utils.logging import get_logger

from services.competitive_intel.schemas import (
    BrandMetrics,
    ProviderMetrics,
    ShareOfVoiceResponse,
    SubstituteInfo,
    SubstitutionPatternResponse,
    CompetitiveGap,
    Opportunity,
    SubstitutionAnalysisResponse,
    OpportunityType,
)

logger = get_logger(__name__)


@dataclass
class BrandPresenceData:
    """Raw brand presence data for analysis."""

    brand_id: uuid.UUID | None
    brand_name: str
    normalized_name: str
    llm_provider: str
    presence: str
    position_rank: int | None
    response_id: uuid.UUID | None = None


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a brand."""

    mention_count: int = 0
    recommendation_count: int = 0
    first_position_count: int = 0
    trusted_count: int = 0
    compared_count: int = 0
    ignored_count: int = 0
    total_responses: int = 0
    position_sum: float = 0.0
    position_count: int = 0

    @property
    def avg_position(self) -> float | None:
        """Calculate average position."""
        if self.position_count > 0:
            return round(self.position_sum / self.position_count, 2)
        return None

    @property
    def visibility_score(self) -> float:
        """
        Calculate visibility score (0-100).

        Formula: (mention_count / total_responses) * 100
        """
        if self.total_responses > 0:
            return round((self.mention_count / self.total_responses) * 100, 2)
        return 0.0

    @property
    def trust_score(self) -> float:
        """
        Calculate trust score (0-100).

        Based on trusted + recommended states as percentage of appearances.
        """
        total_positive = self.trusted_count + self.recommendation_count
        if self.mention_count > 0:
            return round((total_positive / self.mention_count) * 100, 2)
        return 0.0

    @property
    def recommendation_rate(self) -> float:
        """
        Calculate recommendation rate (0-100).

        Formula: (recommendation_count / mention_count) * 100
        """
        if self.mention_count > 0:
            return round((self.recommendation_count / self.mention_count) * 100, 2)
        return 0.0


class AnalysisEngine:
    """
    Core competitive analysis engine.

    Implements all analysis algorithms for competitive intelligence.
    """

    # Weights for opportunity scoring
    VISIBILITY_WEIGHT = 0.25
    RECOMMENDATION_WEIGHT = 0.30
    POSITION_WEIGHT = 0.20
    PROVIDER_COVERAGE_WEIGHT = 0.15
    SUBSTITUTION_WEIGHT = 0.10

    # Thresholds for gap identification
    VISIBILITY_GAP_THRESHOLD = 20.0  # % difference
    RECOMMENDATION_GAP_THRESHOLD = 15.0  # % difference
    POSITION_GAP_THRESHOLD = 2.0  # positions

    def __init__(self):
        """Initialize the analysis engine."""
        self._providers = ["openai", "anthropic", "google", "perplexity"]

    # =========================================================================
    # SHARE OF VOICE CALCULATION
    # =========================================================================

    def calculate_share_of_voice(
        self,
        brand_data: list[BrandPresenceData],
        total_responses_by_provider: dict[str, int],
    ) -> dict[str, AggregatedMetrics]:
        """
        Calculate share of voice for all brands.

        Args:
            brand_data: List of brand presence data points.
            total_responses_by_provider: Total responses per provider.

        Returns:
            Dict mapping normalized brand name to aggregated metrics.
        """
        # Group by brand
        brands: dict[str, dict[str, AggregatedMetrics]] = {}

        for data in brand_data:
            norm_name = data.normalized_name
            provider = data.llm_provider

            if norm_name not in brands:
                brands[norm_name] = {}
            if provider not in brands[norm_name]:
                brands[norm_name][provider] = AggregatedMetrics()

            metrics = brands[norm_name][provider]
            metrics.total_responses = total_responses_by_provider.get(provider, 0)

            # Update counts based on presence
            if data.presence != "ignored":
                metrics.mention_count += 1

                if data.position_rank is not None:
                    metrics.position_sum += data.position_rank
                    metrics.position_count += 1

                    if data.position_rank == 1:
                        metrics.first_position_count += 1

            if data.presence == "recommended":
                metrics.recommendation_count += 1
            elif data.presence == "trusted":
                metrics.trusted_count += 1
            elif data.presence == "compared":
                metrics.compared_count += 1
            elif data.presence == "ignored":
                metrics.ignored_count += 1

        # Aggregate across providers for each brand
        aggregated: dict[str, AggregatedMetrics] = {}
        for norm_name, provider_metrics in brands.items():
            agg = AggregatedMetrics()
            for provider, metrics in provider_metrics.items():
                agg.mention_count += metrics.mention_count
                agg.recommendation_count += metrics.recommendation_count
                agg.first_position_count += metrics.first_position_count
                agg.trusted_count += metrics.trusted_count
                agg.compared_count += metrics.compared_count
                agg.ignored_count += metrics.ignored_count
                agg.total_responses += metrics.total_responses
                agg.position_sum += metrics.position_sum
                agg.position_count += metrics.position_count
            aggregated[norm_name] = agg

        return aggregated

    def calculate_sov_by_provider(
        self,
        brand_data: list[BrandPresenceData],
        total_responses_by_provider: dict[str, int],
        target_brand: str,
    ) -> list[ProviderMetrics]:
        """
        Calculate share of voice broken down by provider for a specific brand.

        Args:
            brand_data: List of brand presence data points.
            total_responses_by_provider: Total responses per provider.
            target_brand: Normalized brand name to analyze.

        Returns:
            List of ProviderMetrics.
        """
        # Filter to target brand
        brand_data = [d for d in brand_data if d.normalized_name == target_brand]

        # Group by provider
        by_provider: dict[str, AggregatedMetrics] = {}

        for data in brand_data:
            provider = data.llm_provider
            if provider not in by_provider:
                by_provider[provider] = AggregatedMetrics()
                by_provider[provider].total_responses = total_responses_by_provider.get(provider, 0)

            metrics = by_provider[provider]

            if data.presence != "ignored":
                metrics.mention_count += 1

                if data.position_rank is not None:
                    metrics.position_sum += data.position_rank
                    metrics.position_count += 1

                    if data.position_rank == 1:
                        metrics.first_position_count += 1

            if data.presence == "recommended":
                metrics.recommendation_count += 1
            elif data.presence == "trusted":
                metrics.trusted_count += 1

        # Convert to ProviderMetrics
        results = []
        for provider, metrics in by_provider.items():
            results.append(ProviderMetrics(
                provider=provider,
                mention_count=metrics.mention_count,
                recommendation_count=metrics.recommendation_count,
                first_position_count=metrics.first_position_count,
                total_responses=metrics.total_responses,
                avg_position=metrics.avg_position,
                visibility_score=metrics.visibility_score,
                recommendation_rate=metrics.recommendation_rate,
            ))

        return sorted(results, key=lambda x: x.visibility_score, reverse=True)

    def build_sov_response(
        self,
        brand_name: str,
        brand_id: uuid.UUID | None,
        aggregated: AggregatedMetrics,
        by_provider: list[ProviderMetrics],
        competitors: list[BrandMetrics],
        period_start: date | None,
        period_end: date | None,
    ) -> ShareOfVoiceResponse:
        """Build ShareOfVoiceResponse from calculated metrics."""
        # Calculate share of voice among all brands
        total_mentions = aggregated.mention_count + sum(c.mention_count for c in competitors)
        sov = (aggregated.mention_count / total_mentions * 100) if total_mentions > 0 else 0.0

        overall = BrandMetrics(
            brand_id=brand_id,
            brand_name=brand_name,
            normalized_name=brand_name.lower().strip(),
            mention_count=aggregated.mention_count,
            recommendation_count=aggregated.recommendation_count,
            first_position_count=aggregated.first_position_count,
            total_responses=aggregated.total_responses,
            avg_position=aggregated.avg_position,
            visibility_score=aggregated.visibility_score,
            trust_score=aggregated.trust_score,
            recommendation_rate=aggregated.recommendation_rate,
            share_of_voice=round(sov, 2),
        )

        return ShareOfVoiceResponse(
            brand_name=brand_name,
            brand_id=brand_id,
            overall_metrics=overall,
            by_provider=by_provider,
            competitors=competitors,
            period_start=period_start,
            period_end=period_end,
        )

    # =========================================================================
    # SUBSTITUTION PATTERN DETECTION
    # =========================================================================

    def detect_substitution_patterns(
        self,
        brand_data: list[BrandPresenceData],
        response_brands: dict[uuid.UUID | str, list[str]],  # response_id -> list of brand names
        target_brand: str | None = None,
    ) -> dict[str, list[SubstituteInfo]]:
        """
        Detect substitution patterns - who appears when target is absent.

        Args:
            brand_data: List of brand presence data.
            response_brands: Map of response_id to list of brands present.
            target_brand: Optional specific brand to analyze.

        Returns:
            Dict mapping missing brand to list of substitutes.
        """
        # Get all unique brands
        all_brands = set(d.normalized_name for d in brand_data)

        if target_brand:
            all_brands = {target_brand.lower().strip()}

        # Get all response IDs
        all_responses = set(d.response_id for d in brand_data if d.response_id)

        substitution_counts: dict[str, dict[str, dict[str, Any]]] = {}

        for missing_brand in all_brands:
            substitution_counts[missing_brand] = {}

            for response_id in all_responses:
                brands_in_response = response_brands.get(response_id, [])
                brands_normalized = [b.lower().strip() for b in brands_in_response]

                # Check if missing_brand is absent in this response
                if missing_brand not in brands_normalized:
                    # Find what brands ARE present (substitutes)
                    for data in brand_data:
                        if (data.response_id == response_id and
                            data.presence != "ignored" and
                            data.normalized_name != missing_brand):

                            sub_name = data.normalized_name
                            if sub_name not in substitution_counts[missing_brand]:
                                substitution_counts[missing_brand][sub_name] = {
                                    "count": 0,
                                    "position_sum": 0.0,
                                    "position_count": 0,
                                    "providers": set(),
                                }

                            info = substitution_counts[missing_brand][sub_name]
                            info["count"] += 1
                            if data.position_rank is not None:
                                info["position_sum"] += data.position_rank
                                info["position_count"] += 1
                            info["providers"].add(data.llm_provider)

        # Convert to SubstituteInfo
        results: dict[str, list[SubstituteInfo]] = {}
        for missing_brand, substitutes in substitution_counts.items():
            results[missing_brand] = []
            total_count = sum(s["count"] for s in substitutes.values())

            for sub_name, info in substitutes.items():
                avg_pos = (info["position_sum"] / info["position_count"]
                           if info["position_count"] > 0 else None)
                rate = (info["count"] / total_count * 100) if total_count > 0 else 0.0

                results[missing_brand].append(SubstituteInfo(
                    brand_name=sub_name,
                    normalized_name=sub_name,
                    occurrence_count=info["count"],
                    avg_position=round(avg_pos, 2) if avg_pos else None,
                    providers=list(info["providers"]),
                    substitution_rate=round(rate, 2),
                ))

            # Sort by occurrence count
            results[missing_brand].sort(key=lambda x: x.occurrence_count, reverse=True)

        return results

    def build_substitution_response(
        self,
        missing_brand: str,
        missing_brand_id: uuid.UUID | None,
        substitutes: list[SubstituteInfo],
        total_absence_count: int,
    ) -> SubstitutionPatternResponse:
        """Build SubstitutionPatternResponse."""
        return SubstitutionPatternResponse(
            missing_brand_name=missing_brand,
            missing_brand_id=missing_brand_id,
            total_absence_count=total_absence_count,
            substitutes=substitutes,
            top_substitute=substitutes[0] if substitutes else None,
        )

    # =========================================================================
    # COMPETITIVE GAP IDENTIFICATION
    # =========================================================================

    def identify_competitive_gaps(
        self,
        tracked_metrics: AggregatedMetrics,
        competitor_metrics: dict[str, AggregatedMetrics],
        tracked_by_provider: list[ProviderMetrics],
    ) -> list[CompetitiveGap]:
        """
        Identify competitive gaps where tracked brand is weaker.

        Args:
            tracked_metrics: Metrics for tracked brand.
            competitor_metrics: Metrics for competitors.
            tracked_by_provider: Tracked brand metrics by provider.

        Returns:
            List of identified competitive gaps.
        """
        gaps = []

        # Check visibility gaps against competitors
        for comp_name, comp_metrics in competitor_metrics.items():
            vis_diff = comp_metrics.visibility_score - tracked_metrics.visibility_score
            if vis_diff > self.VISIBILITY_GAP_THRESHOLD:
                gaps.append(CompetitiveGap(
                    gap_type=OpportunityType.VISIBILITY_GAP,
                    description=f"Competitor '{comp_name}' has {vis_diff:.1f}% higher visibility",
                    severity=min(1.0, vis_diff / 50.0),
                    competitor_name=comp_name,
                    current_value=tracked_metrics.visibility_score,
                    target_value=comp_metrics.visibility_score,
                    improvement_potential=vis_diff,
                ))

            # Check recommendation rate gap
            rec_diff = comp_metrics.recommendation_rate - tracked_metrics.recommendation_rate
            if rec_diff > self.RECOMMENDATION_GAP_THRESHOLD:
                gaps.append(CompetitiveGap(
                    gap_type=OpportunityType.RECOMMENDATION_GAP,
                    description=f"Competitor '{comp_name}' has {rec_diff:.1f}% higher recommendation rate",
                    severity=min(1.0, rec_diff / 40.0),
                    competitor_name=comp_name,
                    current_value=tracked_metrics.recommendation_rate,
                    target_value=comp_metrics.recommendation_rate,
                    improvement_potential=rec_diff,
                ))

            # Check position gap
            if tracked_metrics.avg_position and comp_metrics.avg_position:
                pos_diff = tracked_metrics.avg_position - comp_metrics.avg_position
                if pos_diff > self.POSITION_GAP_THRESHOLD:
                    gaps.append(CompetitiveGap(
                        gap_type=OpportunityType.POSITION_IMPROVEMENT,
                        description=f"Competitor '{comp_name}' ranks {pos_diff:.1f} positions higher on average",
                        severity=min(1.0, pos_diff / 5.0),
                        competitor_name=comp_name,
                        current_value=tracked_metrics.avg_position,
                        target_value=comp_metrics.avg_position,
                        improvement_potential=pos_diff,
                    ))

        # Check provider coverage gaps
        covered_providers = {p.provider for p in tracked_by_provider if p.mention_count > 0}
        missing_providers = set(self._providers) - covered_providers
        for provider in missing_providers:
            gaps.append(CompetitiveGap(
                gap_type=OpportunityType.PROVIDER_EXPANSION,
                description=f"No visibility on {provider.title()}",
                severity=0.7,
                provider=provider,
                current_value=0.0,
                improvement_potential=100.0,
            ))

        # Sort by severity
        gaps.sort(key=lambda x: x.severity, reverse=True)

        return gaps

    # =========================================================================
    # OPPORTUNITY SCORING
    # =========================================================================

    def score_opportunities(
        self,
        gaps: list[CompetitiveGap],
        substitution_defense_needed: list[SubstituteInfo],
    ) -> list[Opportunity]:
        """
        Score and prioritize opportunities based on gaps.

        Args:
            gaps: Identified competitive gaps.
            substitution_defense_needed: Brands frequently substituting tracked brand.

        Returns:
            List of scored opportunities.
        """
        opportunities = []

        # Group gaps by type
        gaps_by_type: dict[OpportunityType, list[CompetitiveGap]] = {}
        for gap in gaps:
            if gap.gap_type not in gaps_by_type:
                gaps_by_type[gap.gap_type] = []
            gaps_by_type[gap.gap_type].append(gap)

        # Create visibility improvement opportunity
        if OpportunityType.VISIBILITY_GAP in gaps_by_type:
            vis_gaps = gaps_by_type[OpportunityType.VISIBILITY_GAP]
            avg_severity = sum(g.severity for g in vis_gaps) / len(vis_gaps)
            competitors = [g.competitor_name for g in vis_gaps if g.competitor_name]

            opportunities.append(Opportunity(
                opportunity_type=OpportunityType.VISIBILITY_GAP,
                description="Improve overall visibility across LLM responses",
                score=avg_severity * 100 * self.VISIBILITY_WEIGHT,
                priority=1 if avg_severity > 0.7 else 2,
                related_competitors=competitors[:5],
                recommended_actions=[
                    "Increase brand mentions in content marketing",
                    "Optimize for common queries in your space",
                    "Build more authoritative content",
                ],
                potential_impact="High visibility improvement",
            ))

        # Create recommendation rate opportunity
        if OpportunityType.RECOMMENDATION_GAP in gaps_by_type:
            rec_gaps = gaps_by_type[OpportunityType.RECOMMENDATION_GAP]
            avg_severity = sum(g.severity for g in rec_gaps) / len(rec_gaps)
            competitors = [g.competitor_name for g in rec_gaps if g.competitor_name]

            opportunities.append(Opportunity(
                opportunity_type=OpportunityType.RECOMMENDATION_GAP,
                description="Increase recommendation rate in LLM responses",
                score=avg_severity * 100 * self.RECOMMENDATION_WEIGHT,
                priority=1 if avg_severity > 0.6 else 2,
                related_competitors=competitors[:5],
                recommended_actions=[
                    "Build more case studies and testimonials",
                    "Improve product differentiation messaging",
                    "Create comparison content highlighting strengths",
                ],
                potential_impact="Higher conversion from LLM referrals",
            ))

        # Create position improvement opportunity
        if OpportunityType.POSITION_IMPROVEMENT in gaps_by_type:
            pos_gaps = gaps_by_type[OpportunityType.POSITION_IMPROVEMENT]
            avg_severity = sum(g.severity for g in pos_gaps) / len(pos_gaps)
            competitors = [g.competitor_name for g in pos_gaps if g.competitor_name]

            opportunities.append(Opportunity(
                opportunity_type=OpportunityType.POSITION_IMPROVEMENT,
                description="Improve ranking position in LLM responses",
                score=avg_severity * 100 * self.POSITION_WEIGHT,
                priority=2 if avg_severity > 0.5 else 3,
                related_competitors=competitors[:5],
                recommended_actions=[
                    "Create more comprehensive product documentation",
                    "Build thought leadership content",
                    "Increase presence in relevant communities",
                ],
                potential_impact="Better first-impression positioning",
            ))

        # Create provider expansion opportunity
        if OpportunityType.PROVIDER_EXPANSION in gaps_by_type:
            prov_gaps = gaps_by_type[OpportunityType.PROVIDER_EXPANSION]
            providers = [g.provider for g in prov_gaps if g.provider]

            opportunities.append(Opportunity(
                opportunity_type=OpportunityType.PROVIDER_EXPANSION,
                description=f"Expand visibility to: {', '.join(providers)}",
                score=len(providers) * 25 * self.PROVIDER_COVERAGE_WEIGHT,
                priority=3,
                related_providers=providers,
                recommended_actions=[
                    "Research content strategies for each provider",
                    "Monitor competitor presence on missing providers",
                    "Create provider-specific optimization strategies",
                ],
                potential_impact="Broader market reach",
            ))

        # Create substitution defense opportunity
        if substitution_defense_needed:
            top_subs = substitution_defense_needed[:5]
            competitors = [s.brand_name for s in top_subs]
            avg_rate = sum(s.substitution_rate for s in top_subs) / len(top_subs)

            opportunities.append(Opportunity(
                opportunity_type=OpportunityType.SUBSTITUTION_DEFENSE,
                description="Defend against competitors substituting your brand",
                score=avg_rate * self.SUBSTITUTION_WEIGHT,
                priority=2 if avg_rate > 20 else 3,
                related_competitors=competitors,
                recommended_actions=[
                    f"Analyze why '{competitors[0]}' is frequently recommended instead",
                    "Improve differentiation from top substitutes",
                    "Create head-to-head comparison content",
                ],
                potential_impact="Reduced competitive displacement",
            ))

        # Sort by score
        opportunities.sort(key=lambda x: x.score, reverse=True)

        # Re-assign priorities based on final ranking
        for i, opp in enumerate(opportunities):
            opp.priority = min(5, i + 1)

        return opportunities

    def calculate_overall_opportunity_score(
        self,
        opportunities: list[Opportunity],
    ) -> float:
        """Calculate overall opportunity score (0-100)."""
        if not opportunities:
            return 0.0

        # Weighted sum of opportunity scores
        total = sum(o.score for o in opportunities)
        # Normalize to 0-100 range
        return min(100.0, round(total, 2))

    # =========================================================================
    # FULL ANALYSIS
    # =========================================================================

    def run_full_analysis(
        self,
        website_id: uuid.UUID,
        tracked_brand: str,
        tracked_brand_id: uuid.UUID | None,
        brand_data: list[BrandPresenceData],
        total_responses_by_provider: dict[str, int],
        response_brands: dict[uuid.UUID | str, list[str]],
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> SubstitutionAnalysisResponse:
        """
        Run full competitive analysis.

        Args:
            website_id: Website being analyzed.
            tracked_brand: Primary brand name.
            tracked_brand_id: Primary brand UUID.
            brand_data: All brand presence data.
            total_responses_by_provider: Total responses per provider.
            response_brands: Map of response_id to brands present.
            period_start: Analysis period start.
            period_end: Analysis period end.

        Returns:
            Complete SubstitutionAnalysisResponse.
        """
        normalized_tracked = tracked_brand.lower().strip()

        # 1. Calculate share of voice
        all_sov = self.calculate_share_of_voice(brand_data, total_responses_by_provider)
        tracked_metrics = all_sov.get(normalized_tracked, AggregatedMetrics())

        # 2. Get tracked brand SOV by provider
        by_provider = self.calculate_sov_by_provider(
            brand_data, total_responses_by_provider, normalized_tracked
        )

        # 3. Build competitor metrics
        competitor_metrics = {k: v for k, v in all_sov.items() if k != normalized_tracked}
        competitors = []
        for name, metrics in sorted(
            competitor_metrics.items(),
            key=lambda x: x[1].visibility_score,
            reverse=True
        )[:20]:
            total_mentions = sum(m.mention_count for m in all_sov.values())
            sov = (metrics.mention_count / total_mentions * 100) if total_mentions > 0 else 0.0
            competitors.append(BrandMetrics(
                brand_name=name,
                normalized_name=name,
                mention_count=metrics.mention_count,
                recommendation_count=metrics.recommendation_count,
                first_position_count=metrics.first_position_count,
                total_responses=metrics.total_responses,
                avg_position=metrics.avg_position,
                visibility_score=metrics.visibility_score,
                trust_score=metrics.trust_score,
                recommendation_rate=metrics.recommendation_rate,
                share_of_voice=round(sov, 2),
            ))

        # 4. Build SOV response
        sov_response = self.build_sov_response(
            tracked_brand, tracked_brand_id, tracked_metrics,
            by_provider, competitors, period_start, period_end
        )

        # 5. Detect substitution patterns
        all_substitutions = self.detect_substitution_patterns(
            brand_data, response_brands, target_brand=None
        )

        # Who substitutes tracked brand?
        tracked_substitutes = all_substitutions.get(normalized_tracked, [])

        # Who does tracked brand substitute?
        brands_tracked_substitutes = []
        for missing, subs in all_substitutions.items():
            for sub in subs:
                if sub.normalized_name == normalized_tracked:
                    brands_tracked_substitutes.append(SubstituteInfo(
                        brand_name=missing,
                        normalized_name=missing,
                        occurrence_count=sub.occurrence_count,
                        avg_position=sub.avg_position,
                        providers=sub.providers,
                        substitution_rate=sub.substitution_rate,
                    ))

        # Build substitution pattern responses for top brands
        substitution_responses = []
        for brand_name, subs in list(all_substitutions.items())[:10]:
            if subs:
                total_absence = sum(s.occurrence_count for s in subs)
                substitution_responses.append(self.build_substitution_response(
                    brand_name, None, subs[:10], total_absence
                ))

        # 6. Identify competitive gaps
        gaps = self.identify_competitive_gaps(
            tracked_metrics, competitor_metrics, by_provider
        )

        # 7. Score opportunities
        opportunities = self.score_opportunities(gaps, tracked_substitutes)
        overall_score = self.calculate_overall_opportunity_score(opportunities)

        # 8. Build summary
        summary = {
            "total_brands_analyzed": len(all_sov),
            "total_responses_analyzed": sum(total_responses_by_provider.values()),
            "tracked_brand_visibility": tracked_metrics.visibility_score,
            "tracked_brand_recommendation_rate": tracked_metrics.recommendation_rate,
            "top_competitor": competitors[0].brand_name if competitors else None,
            "providers_with_presence": len([p for p in by_provider if p.mention_count > 0]),
            "total_providers": len(self._providers),
            "gaps_identified": len(gaps),
            "opportunities_count": len(opportunities),
        }

        return SubstitutionAnalysisResponse(
            website_id=website_id,
            tracked_brand=tracked_brand,
            share_of_voice=sov_response,
            substitution_patterns=substitution_responses,
            brands_substituting_tracked=tracked_substitutes[:10],
            brands_tracked_substitutes=brands_tracked_substitutes[:10],
            competitive_gaps=gaps,
            opportunities=opportunities,
            overall_opportunity_score=overall_score,
            summary=summary,
        )
