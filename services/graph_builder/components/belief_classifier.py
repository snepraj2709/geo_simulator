"""
Belief Type Classifier for Knowledge Graph Builder.

Classifies belief types from LLM response text to determine
what beliefs are being installed about brands.

Belief Types (from ARCHITECTURE.md):
- truth: epistemic clarity, neutrality
- superiority: better than alternatives
- outcome: ROI, performance, results
- transaction: buy now, act
- identity: people like you use this
- social_proof: others chose this
"""

import re
from dataclasses import dataclass, field
from typing import Any

from shared.utils.logging import get_logger

from services.graph_builder.schemas import (
    BeliefTypeEnum,
    PresenceStateEnum,
    IntentTypeEnum,
    FunnelStageEnum,
)

logger = get_logger(__name__)


@dataclass
class BeliefClassification:
    """Result of belief type classification."""

    belief_type: BeliefTypeEnum
    confidence: float
    signals: list[str] = field(default_factory=list)
    context_snippet: str | None = None


@dataclass
class BeliefAnalysis:
    """Full belief analysis for a brand mention."""

    brand_name: str
    primary_belief: BeliefClassification | None
    all_beliefs: list[BeliefClassification] = field(default_factory=list)
    presence_state: PresenceStateEnum | None = None
    intent_type: IntentTypeEnum | None = None


class BeliefClassifier:
    """
    Classifies belief types installed by LLM responses.

    Implements belief type detection as defined in ARCHITECTURE.md:
    - Analyzes text context around brand mentions
    - Considers presence state and intent type for context
    - Produces confidence-weighted belief classifications
    """

    # Pattern definitions with weights
    # Higher weight = stronger signal for that belief type

    TRUTH_PATTERNS = [
        # Factual/epistemic patterns
        (r"\bin\s+fact\b", 1.0, "factual_statement"),
        (r"\bactually\b", 0.7, "clarification"),
        (r"\bobjectively\b", 0.9, "objective_claim"),
        (r"\bdata\s+shows\b", 0.95, "data_backed"),
        (r"\bstudies\s+(?:show|indicate|suggest)\b", 0.9, "study_reference"),
        (r"\bresearch\s+(?:shows|indicates|suggests)\b", 0.9, "research_backed"),
        (r"\baccording\s+to\b", 0.7, "attribution"),
        (r"\bevidence\s+(?:shows|suggests)\b", 0.9, "evidence_based"),
        (r"\bstatistics?\s+(?:show|indicate)\b", 0.9, "statistical"),
        (r"\btechnically\b", 0.7, "technical_fact"),
        (r"\bscientifically\b", 0.8, "scientific"),
        (r"\bverified\b", 0.8, "verified"),
        (r"\bdocumented\b", 0.7, "documented"),
        (r"\bproven\b", 0.85, "proven"),
        (r"\bestablished\b", 0.7, "established"),
        (r"\bfoundational\b", 0.6, "foundational"),
    ]

    SUPERIORITY_PATTERNS = [
        # Competitive advantage patterns
        (r"\bbest\b", 0.9, "superlative"),
        (r"\btop(?:-tier|\s+choice)?\b", 0.8, "top_ranking"),
        (r"\b#1\b", 1.0, "number_one"),
        (r"\bnumber\s+one\b", 1.0, "number_one"),
        (r"\bleading\b", 0.8, "market_leader"),
        (r"\bsuperior\b", 1.0, "explicit_superior"),
        (r"\boutperforms?\b", 0.95, "outperformance"),
        (r"\bunmatched\b", 0.9, "unmatched"),
        (r"\bunrivaled\b", 0.9, "unrivaled"),
        (r"\bmarket\s+leader\b", 0.95, "market_leader"),
        (r"\bindustry\s+leader\b", 0.95, "industry_leader"),
        (r"\bmost\s+(?:popular|advanced|powerful|comprehensive)\b", 0.85, "most_superlative"),
        (r"\bbeats?\b", 0.8, "competitive_beat"),
        (r"\bexceeds?\b", 0.7, "exceeds"),
        (r"\bstands?\s+out\b", 0.8, "stands_out"),
        (r"\bsecond\s+to\s+none\b", 1.0, "second_to_none"),
        (r"\bbetter\s+than\b", 0.85, "comparative"),
        (r"\bmore\s+(?:powerful|capable|advanced)\s+than\b", 0.9, "comparative_adv"),
    ]

    OUTCOME_PATTERNS = [
        # ROI/performance/results patterns
        (r"\bROI\b", 1.0, "roi_explicit"),
        (r"\breturn\s+on\s+investment\b", 1.0, "roi_full"),
        (r"\bresults?\b", 0.6, "results"),
        (r"\bperformance\b", 0.7, "performance"),
        (r"\befficiency\b", 0.8, "efficiency"),
        (r"\bincreases?\s+(?:productivity|revenue|sales)\b", 0.9, "increase_metric"),
        (r"\bimproves?\s+(?:productivity|efficiency|outcomes?)\b", 0.85, "improvement"),
        (r"\bboosts?\b", 0.7, "boost"),
        (r"\bsaves?\s+(?:time|money|costs?|hours?)\b", 0.95, "cost_savings"),
        (r"\b(?:\d+%|percent)\s+(?:faster|better|improvement|increase)\b", 0.95, "quantified_result"),
        (r"\bproductivity\b", 0.8, "productivity"),
        (r"\bgrowth\b", 0.6, "growth"),
        (r"\bscalability\b", 0.7, "scalability"),
        (r"\breliability\b", 0.7, "reliability"),
        (r"\bstreamlines?\b", 0.7, "streamline"),
        (r"\bautomation\b", 0.6, "automation"),
        (r"\btime-saving\b", 0.85, "time_saving"),
        (r"\bcost-effective\b", 0.85, "cost_effective"),
        (r"\bvalue\b", 0.5, "value"),
        (r"\bbenefits?\b", 0.5, "benefits"),
    ]

    TRANSACTION_PATTERNS = [
        # Call-to-action/conversion patterns
        (r"\bfree\s+trial\b", 1.0, "free_trial"),
        (r"\bsign\s+up\b", 0.9, "sign_up"),
        (r"\bget\s+started\b", 0.9, "get_started"),
        (r"\bpricing\b", 0.8, "pricing"),
        (r"\bsubscribe\b", 0.85, "subscribe"),
        (r"\bpurchase\b", 0.9, "purchase"),
        (r"\bbuy\s+now\b", 1.0, "buy_now"),
        (r"\blimited\s+(?:time|offer)\b", 0.9, "urgency"),
        (r"\bdiscount\b", 0.8, "discount"),
        (r"\bbook\s+a\s+demo\b", 0.95, "demo_cta"),
        (r"\bstart\s+(?:free|today|now)\b", 0.9, "start_cta"),
        (r"\b(?:download|install)\s+(?:free|now)?\b", 0.85, "download_cta"),
        (r"\bclick\s+here\b", 0.85, "click_cta"),
        (r"\btry\s+(?:it\s+)?(?:free|now|today)\b", 0.9, "try_cta"),
        (r"\bspecial\s+offer\b", 0.9, "special_offer"),
        (r"\bact\s+now\b", 0.95, "urgency_cta"),
        (r"\bdon't\s+miss\b", 0.8, "fomo"),
    ]

    IDENTITY_PATTERNS = [
        # Target audience/persona patterns
        (r"\bfor\s+(?:teams|developers|businesses|enterprises|professionals)\b", 0.9, "target_audience"),
        (r"\bdesigned\s+for\b", 0.85, "designed_for"),
        (r"\bperfect\s+for\b", 0.9, "perfect_for"),
        (r"\bideal\s+for\b", 0.9, "ideal_for"),
        (r"\bmade\s+for\b", 0.85, "made_for"),
        (r"\b(?:if\s+)?you(?:'re|\s+are)\s+(?:a|an)\b", 0.8, "persona_match"),
        (r"\bprofessionals?\s+like\s+you\b", 0.95, "like_you"),
        (r"\bsmall\s+business(?:es)?\b", 0.8, "small_business"),
        (r"\bstartups?\b", 0.7, "startup"),
        (r"\benterprise(?:-grade)?\b", 0.7, "enterprise"),
        (r"\bfor\s+people\s+who\b", 0.85, "for_people_who"),
        (r"\b(?:tailored|customized)\s+(?:for|to)\b", 0.8, "tailored"),
        (r"\byour\s+(?:team|company|business|organization)\b", 0.75, "your_org"),
        (r"\bbuilt\s+(?:for|by)\s+(?:developers|teams|experts)\b", 0.85, "built_for"),
    ]

    SOCIAL_PROOF_PATTERNS = [
        # Social validation patterns
        (r"\bmillions?\s+(?:of\s+)?(?:users?|people|customers?)\b", 1.0, "millions_users"),
        (r"\bthousands?\s+(?:of\s+)?(?:companies|businesses|teams)\b", 0.95, "thousands_companies"),
        (r"\bwidely\s+used\b", 0.9, "widely_used"),
        (r"\bpopular\s+choice\b", 0.9, "popular_choice"),
        (r"\bmany\s+(?:companies|businesses|teams|organizations)\b", 0.8, "many_orgs"),
        (r"\btrusted\s+by\b", 0.95, "trusted_by"),
        (r"\bused\s+by\b", 0.7, "used_by"),
        (r"\bcustomers?\s+(?:love|choose|prefer|trust)\b", 0.9, "customer_sentiment"),
        (r"\b(?:reviews?|ratings?|stars?)\b", 0.7, "reviews"),
        (r"\btestimonials?\b", 0.85, "testimonials"),
        (r"\bcase\s+stud(?:y|ies)\b", 0.8, "case_studies"),
        (r"\bfortune\s+\d+\b", 0.95, "fortune_500"),
        (r"\baward-winning\b", 0.85, "award_winning"),
        (r"\bhighly\s+rated\b", 0.85, "highly_rated"),
        (r"\b(?:\d+[kKmM]?\+?)\s+(?:customers?|users?|companies)\b", 0.9, "user_count"),
        (r"\bcommunity\s+of\b", 0.7, "community"),
        (r"\bworld(?:wide|'s)\b", 0.6, "worldwide"),
        (r"\bglobal(?:ly)?\b", 0.5, "global"),
    ]

    # Context modifiers based on presence state
    PRESENCE_BELIEF_AFFINITY = {
        PresenceStateEnum.RECOMMENDED: {
            BeliefTypeEnum.OUTCOME: 1.2,
            BeliefTypeEnum.SUPERIORITY: 1.1,
            BeliefTypeEnum.TRANSACTION: 1.3,
        },
        PresenceStateEnum.TRUSTED: {
            BeliefTypeEnum.TRUTH: 1.3,
            BeliefTypeEnum.SOCIAL_PROOF: 1.2,
        },
        PresenceStateEnum.COMPARED: {
            BeliefTypeEnum.SUPERIORITY: 1.2,
            BeliefTypeEnum.OUTCOME: 1.1,
        },
        PresenceStateEnum.MENTIONED: {
            BeliefTypeEnum.TRUTH: 1.1,
        },
    }

    # Intent type modifiers
    INTENT_BELIEF_AFFINITY = {
        IntentTypeEnum.DECISION: {
            BeliefTypeEnum.TRANSACTION: 1.3,
            BeliefTypeEnum.OUTCOME: 1.2,
            BeliefTypeEnum.SOCIAL_PROOF: 1.1,
        },
        IntentTypeEnum.EVALUATION: {
            BeliefTypeEnum.SUPERIORITY: 1.2,
            BeliefTypeEnum.OUTCOME: 1.2,
            BeliefTypeEnum.TRUTH: 1.1,
        },
        IntentTypeEnum.INFORMATIONAL: {
            BeliefTypeEnum.TRUTH: 1.3,
            BeliefTypeEnum.IDENTITY: 1.1,
        },
    }

    def __init__(self):
        """Initialize the belief classifier."""
        self._compiled_patterns = {
            BeliefTypeEnum.TRUTH: self._compile_patterns(self.TRUTH_PATTERNS),
            BeliefTypeEnum.SUPERIORITY: self._compile_patterns(self.SUPERIORITY_PATTERNS),
            BeliefTypeEnum.OUTCOME: self._compile_patterns(self.OUTCOME_PATTERNS),
            BeliefTypeEnum.TRANSACTION: self._compile_patterns(self.TRANSACTION_PATTERNS),
            BeliefTypeEnum.IDENTITY: self._compile_patterns(self.IDENTITY_PATTERNS),
            BeliefTypeEnum.SOCIAL_PROOF: self._compile_patterns(self.SOCIAL_PROOF_PATTERNS),
        }

    def _compile_patterns(
        self,
        patterns: list[tuple[str, float, str]],
    ) -> list[tuple[re.Pattern, float, str]]:
        """Compile regex patterns."""
        compiled = []
        for pattern, weight, signal in patterns:
            try:
                compiled.append((re.compile(pattern, re.IGNORECASE), weight, signal))
            except re.error as e:
                logger.warning(f"Failed to compile pattern: {pattern}, error: {e}")
        return compiled

    def classify_belief(
        self,
        context: str,
        brand_name: str | None = None,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
    ) -> BeliefClassification | None:
        """
        Classify the primary belief type from context.

        Args:
            context: Text context around the brand mention.
            brand_name: Optional brand name for context extraction.
            presence_state: Optional presence state for score adjustment.
            intent_type: Optional intent type for score adjustment.

        Returns:
            BeliefClassification with the dominant belief type, or None.
        """
        if not context:
            return None

        # Get base scores from pattern matching
        scores = self._calculate_belief_scores(context)

        if not any(score for score, _ in scores.values()):
            return None

        # Apply presence state modifiers
        if presence_state and presence_state in self.PRESENCE_BELIEF_AFFINITY:
            modifiers = self.PRESENCE_BELIEF_AFFINITY[presence_state]
            for belief, modifier in modifiers.items():
                score, signals = scores[belief]
                scores[belief] = (score * modifier, signals)

        # Apply intent type modifiers
        if intent_type and intent_type in self.INTENT_BELIEF_AFFINITY:
            modifiers = self.INTENT_BELIEF_AFFINITY[intent_type]
            for belief, modifier in modifiers.items():
                score, signals = scores[belief]
                scores[belief] = (score * modifier, signals)

        # Find dominant belief
        max_score = 0.0
        dominant_belief = None
        signals = []

        for belief, (score, belief_signals) in scores.items():
            if score > max_score:
                max_score = score
                dominant_belief = belief
                signals = belief_signals

        if dominant_belief is None or max_score == 0:
            return None

        # Normalize confidence (0-1 scale)
        confidence = min(1.0, max_score / 5.0)

        return BeliefClassification(
            belief_type=dominant_belief,
            confidence=confidence,
            signals=signals[:5],
            context_snippet=context[:200] if context else None,
        )

    def classify_all_beliefs(
        self,
        context: str,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
        min_confidence: float = 0.1,
    ) -> list[BeliefClassification]:
        """
        Classify all belief types present in context.

        Args:
            context: Text context to analyze.
            presence_state: Optional presence state for adjustment.
            intent_type: Optional intent type for adjustment.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of BeliefClassification sorted by confidence.
        """
        if not context:
            return []

        scores = self._calculate_belief_scores(context)

        # Apply modifiers
        if presence_state and presence_state in self.PRESENCE_BELIEF_AFFINITY:
            modifiers = self.PRESENCE_BELIEF_AFFINITY[presence_state]
            for belief, modifier in modifiers.items():
                score, signals = scores[belief]
                scores[belief] = (score * modifier, signals)

        if intent_type and intent_type in self.INTENT_BELIEF_AFFINITY:
            modifiers = self.INTENT_BELIEF_AFFINITY[intent_type]
            for belief, modifier in modifiers.items():
                score, signals = scores[belief]
                scores[belief] = (score * modifier, signals)

        # Build classifications
        classifications = []
        for belief, (score, signals) in scores.items():
            if score > 0:
                confidence = min(1.0, score / 5.0)
                if confidence >= min_confidence:
                    classifications.append(BeliefClassification(
                        belief_type=belief,
                        confidence=confidence,
                        signals=signals[:5],
                    ))

        # Sort by confidence descending
        classifications.sort(key=lambda x: x.confidence, reverse=True)

        return classifications

    def _calculate_belief_scores(
        self,
        context: str,
    ) -> dict[BeliefTypeEnum, tuple[float, list[str]]]:
        """
        Calculate raw belief scores from pattern matching.

        Returns dict mapping belief type to (score, signals).
        """
        scores = {belief: (0.0, []) for belief in BeliefTypeEnum}

        for belief, patterns in self._compiled_patterns.items():
            total_score = 0.0
            signals = []

            for pattern, weight, signal in patterns:
                matches = pattern.findall(context)
                if matches:
                    # Score increases with weight and match count, but diminishing returns
                    match_score = weight * (1 + 0.3 * (len(matches) - 1))
                    total_score += match_score
                    signals.append(signal)

            scores[belief] = (total_score, signals)

        return scores

    def analyze_brand_beliefs(
        self,
        response_text: str,
        brand_name: str,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
        context_window: int = 200,
    ) -> BeliefAnalysis:
        """
        Analyze beliefs installed about a specific brand.

        Args:
            response_text: Full LLM response text.
            brand_name: Brand name to analyze.
            presence_state: Brand's presence state.
            intent_type: Query intent type.
            context_window: Characters around brand mention to analyze.

        Returns:
            BeliefAnalysis with primary and all detected beliefs.
        """
        # Extract context around brand mention
        context = self._extract_brand_context(response_text, brand_name, context_window)

        if not context:
            return BeliefAnalysis(
                brand_name=brand_name,
                primary_belief=None,
                presence_state=presence_state,
                intent_type=intent_type,
            )

        # Get all beliefs
        all_beliefs = self.classify_all_beliefs(
            context,
            presence_state=presence_state,
            intent_type=intent_type,
        )

        # Primary is the highest confidence
        primary = all_beliefs[0] if all_beliefs else None

        return BeliefAnalysis(
            brand_name=brand_name,
            primary_belief=primary,
            all_beliefs=all_beliefs,
            presence_state=presence_state,
            intent_type=intent_type,
        )

    def _extract_brand_context(
        self,
        text: str,
        brand_name: str,
        window: int = 200,
    ) -> str | None:
        """Extract context around brand mention."""
        text_lower = text.lower()
        brand_lower = brand_name.lower()

        pos = text_lower.find(brand_lower)
        if pos < 0:
            return None

        start = max(0, pos - window)
        end = min(len(text), pos + len(brand_name) + window)

        return text[start:end]

    def get_belief_distribution(
        self,
        classifications: list[BeliefClassification],
    ) -> dict[str, float]:
        """
        Get normalized belief distribution from classifications.

        Returns dict mapping belief type value to normalized percentage.
        """
        if not classifications:
            return {}

        total = sum(c.confidence for c in classifications)
        if total == 0:
            return {}

        return {
            c.belief_type.value: round(c.confidence / total * 100, 1)
            for c in classifications
        }
