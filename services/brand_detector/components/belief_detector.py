"""
Belief Type Detector.

Detects the type of belief installed by LLM responses
for each brand mention.
"""

import re
from dataclasses import dataclass

from shared.utils.logging import get_logger

from services.brand_detector.schemas import BeliefType

logger = get_logger(__name__)


@dataclass
class BeliefMatch:
    """A belief type match result."""

    belief: BeliefType
    pattern_name: str
    confidence: float = 1.0


class BeliefTypeDetector:
    """
    Detects belief types from LLM responses.

    Belief types from DATA_MODEL.md:
    - truth: epistemic clarity, neutrality
    - superiority: better than alternatives
    - outcome: ROI, performance, results
    - transaction: buy now, act
    - identity: people like you use this
    - social_proof: others chose this
    """

    # Patterns for TRUTH belief
    # Epistemic clarity, neutrality, factual statements
    TRUTH_PATTERNS = [
        (r"\bin\s+fact\b", 1.0),
        (r"\bactually\b", 0.8),
        (r"\bobjectively\b", 0.9),
        (r"\bdata\s+shows\b", 0.95),
        (r"\bstudies\s+(?:show|indicate|suggest)\b", 0.9),
        (r"\bresearch\s+(?:shows|indicates|suggests)\b", 0.9),
        (r"\baccording\s+to\b", 0.7),
        (r"\bevidence\s+(?:shows|suggests)\b", 0.9),
        (r"\bstatistics\s+(?:show|indicate)\b", 0.9),
        (r"\btechnically\b", 0.7),
        (r"\bscientifically\b", 0.8),
        (r"\bverified\b", 0.8),
        (r"\bdocumented\b", 0.7),
        (r"\bfacts?\s+(?:are|is)\b", 0.8),
    ]

    # Patterns for SUPERIORITY belief
    # Better than alternatives
    SUPERIORITY_PATTERNS = [
        (r"\bbest\b", 0.9),
        (r"\btop\b", 0.7),
        (r"\b#1\b", 1.0),
        (r"\bnumber\s+one\b", 1.0),
        (r"\bleading\b", 0.8),
        (r"\bsuperior\b", 1.0),
        (r"\boutperforms?\b", 0.95),
        (r"\bunmatched\b", 0.9),
        (r"\bunrivaled\b", 0.9),
        (r"\bmarket\s+leader\b", 0.95),
        (r"\bindustry\s+leader\b", 0.95),
        (r"\bmost\s+(?:popular|advanced|powerful)\b", 0.85),
        (r"\bbeats?\b", 0.8),
        (r"\bexceeds?\b", 0.7),
        (r"\bstands?\s+out\b", 0.8),
        (r"\bsecond\s+to\s+none\b", 1.0),
    ]

    # Patterns for OUTCOME belief
    # ROI, performance, results
    OUTCOME_PATTERNS = [
        (r"\bROI\b", 1.0),
        (r"\breturn\s+on\s+investment\b", 1.0),
        (r"\bresults?\b", 0.7),
        (r"\bperformance\b", 0.7),
        (r"\befficiency\b", 0.8),
        (r"\bincreases?\b", 0.6),
        (r"\bimproves?\b", 0.6),
        (r"\bboosts?\b", 0.7),
        (r"\bsaves?\s+(?:time|money|costs?)\b", 0.9),
        (r"\b(?:\d+%|percent)\s+(?:faster|better|improvement)\b", 0.95),
        (r"\bproductivity\b", 0.8),
        (r"\bgrowth\b", 0.6),
        (r"\bscalability\b", 0.7),
        (r"\breliability\b", 0.7),
        (r"\b(?:faster|quicker|more\s+efficient)\b", 0.7),
        (r"\bstreamlines?\b", 0.7),
        (r"\bautomation\b", 0.6),
    ]

    # Patterns for TRANSACTION belief
    # Buy now, act, convert
    TRANSACTION_PATTERNS = [
        (r"\bfree\s+trial\b", 1.0),
        (r"\bsign\s+up\b", 0.9),
        (r"\bget\s+started\b", 0.9),
        (r"\bpricing\b", 0.8),
        (r"\bsubscribe\b", 0.85),
        (r"\bpurchase\b", 0.9),
        (r"\bbuy\s+now\b", 1.0),
        (r"\btoday\b", 0.5),
        (r"\bnow\b", 0.4),
        (r"\blimited\s+(?:time|offer)\b", 0.9),
        (r"\bdiscount\b", 0.8),
        (r"\bbook\s+a\s+demo\b", 0.95),
        (r"\bstart\s+(?:free|today|now)\b", 0.9),
        (r"\b(?:download|install)\s+(?:free|now)\b", 0.9),
        (r"\bclick\s+here\b", 0.85),
        (r"\bvisit\b", 0.5),
    ]

    # Patterns for IDENTITY belief
    # People like you use this
    IDENTITY_PATTERNS = [
        (r"\bfor\s+(?:teams|developers|businesses|enterprises)\b", 0.9),
        (r"\bdesigned\s+for\b", 0.85),
        (r"\bperfect\s+for\b", 0.9),
        (r"\bideal\s+for\b", 0.9),
        (r"\bmade\s+for\b", 0.85),
        (r"\b(?:if\s+)?you(?:'re|\s+are)\s+(?:a|an)\b", 0.8),
        (r"\bprofessionals?\b", 0.6),
        (r"\bexperts?\b", 0.6),
        (r"\bsmall\s+business(?:es)?\b", 0.8),
        (r"\bstartups?\b", 0.7),
        (r"\benterprise\b", 0.7),
        (r"\blike\s+(?:you|yours)\b", 0.9),
        (r"\bfor\s+people\s+who\b", 0.85),
        (r"\b(?:tailored|customized)\s+(?:for|to)\b", 0.8),
    ]

    # Patterns for SOCIAL_PROOF belief
    # Others chose this
    SOCIAL_PROOF_PATTERNS = [
        (r"\bmillions?\s+(?:of\s+)?(?:users?|people|customers?)\b", 1.0),
        (r"\bthousands?\s+(?:of\s+)?(?:companies|businesses)\b", 0.95),
        (r"\bwidely\s+used\b", 0.9),
        (r"\bpopular\s+choice\b", 0.9),
        (r"\bmany\s+(?:companies|businesses|teams)\b", 0.8),
        (r"\btrusted\s+by\b", 0.95),
        (r"\bused\s+by\b", 0.7),
        (r"\bcustomers?\s+(?:love|choose|prefer)\b", 0.9),
        (r"\b(?:reviews?|ratings?|stars?)\b", 0.7),
        (r"\btestimonials?\b", 0.85),
        (r"\bcase\s+stud(?:y|ies)\b", 0.8),
        (r"\bfortune\s+\d+\b", 0.9),
        (r"\baward-winning\b", 0.85),
        (r"\bhighly\s+rated\b", 0.85),
        (r"\b(?:\d+\+?)\s+(?:customers?|users?|companies)\b", 0.9),
        (r"\bcommunity\b", 0.5),
    ]

    def __init__(self):
        """Initialize the belief type detector."""
        self._compiled_patterns = {
            BeliefType.TRUTH: self._compile_patterns(self.TRUTH_PATTERNS),
            BeliefType.SUPERIORITY: self._compile_patterns(self.SUPERIORITY_PATTERNS),
            BeliefType.OUTCOME: self._compile_patterns(self.OUTCOME_PATTERNS),
            BeliefType.TRANSACTION: self._compile_patterns(self.TRANSACTION_PATTERNS),
            BeliefType.IDENTITY: self._compile_patterns(self.IDENTITY_PATTERNS),
            BeliefType.SOCIAL_PROOF: self._compile_patterns(self.SOCIAL_PROOF_PATTERNS),
        }

    def _compile_patterns(
        self,
        patterns: list[tuple[str, float]],
    ) -> list[tuple[re.Pattern, float]]:
        """Compile regex patterns."""
        compiled = []
        for pattern, weight in patterns:
            try:
                compiled.append((re.compile(pattern, re.IGNORECASE), weight))
            except re.error as e:
                logger.warning(f"Failed to compile pattern: {pattern}, error: {e}")
        return compiled

    def detect_belief(
        self,
        context: str,
    ) -> tuple[BeliefType | None, float, list[str]]:
        """
        Detect the dominant belief type in the context.

        Args:
            context: Text context around a brand mention.

        Returns:
            Tuple of (belief_type, confidence, signals) or (None, 0, [])
        """
        scores = {belief: 0.0 for belief in BeliefType}
        signals = []

        # Check each belief type
        for belief, patterns in self._compiled_patterns.items():
            for pattern, weight in patterns:
                matches = pattern.findall(context)
                if matches:
                    scores[belief] += weight * len(matches)
                    signals.append(f"{belief.value}:{pattern.pattern[:25]}")

        # Find dominant belief
        max_score = 0.0
        dominant = None

        for belief, score in scores.items():
            if score > max_score:
                max_score = score
                dominant = belief

        if dominant is None:
            return None, 0.0, []

        # Normalize confidence
        confidence = min(1.0, max_score / 3.0)

        return dominant, confidence, signals[:3]

    def detect_all_beliefs(
        self,
        context: str,
    ) -> list[tuple[BeliefType, float]]:
        """
        Detect all belief types present in the context with their scores.

        Args:
            context: Text context to analyze.

        Returns:
            List of (belief_type, score) tuples, sorted by score descending.
        """
        scores = []

        for belief, patterns in self._compiled_patterns.items():
            total_score = 0.0
            for pattern, weight in patterns:
                matches = pattern.findall(context)
                total_score += weight * len(matches)

            if total_score > 0:
                scores.append((belief, total_score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores
