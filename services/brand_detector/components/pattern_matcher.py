"""
Presence Pattern Matcher.

Pattern matching engine for detecting brand presence states
using regex patterns and contextual analysis.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from shared.utils.logging import get_logger

from services.brand_detector.schemas import BrandPresenceState

logger = get_logger(__name__)


@dataclass
class PresenceMatch:
    """A pattern match result."""

    presence: BrandPresenceState
    pattern_name: str
    match_text: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0


@dataclass
class PatternSet:
    """Set of patterns for a presence state."""

    presence: BrandPresenceState
    patterns: list[tuple[str, float]]  # (pattern, confidence_weight)


class PresencePatternMatcher:
    """
    Pattern matching engine for brand presence detection.

    Implements the presence state definitions from ARCHITECTURE.md:
    - ignored: Brand not mentioned at all
    - mentioned: Brand name appears but without context
    - trusted: Brand cited as authority without sales push
    - recommended: Brand with clear call-to-action
    - compared: Brand in neutral evaluation context

    Rule: One dominant state per brand per answer.
    """

    # Patterns for RECOMMENDED state (highest priority)
    # Brand with clear call-to-action
    RECOMMENDED_PATTERNS = [
        (r"\b(?:i\s+)?(?:highly\s+)?recommend\b", 1.0),
        (r"\bstrongly\s+(?:suggest|recommend)\b", 1.0),
        (r"\byou\s+should\s+(?:try|use|consider|go\s+with)\b", 0.95),
        (r"\b(?:best|top)\s+(?:choice|pick|option)\b", 0.9),
        (r"\b(?:go\s+with|choose|pick)\s+\w+\b", 0.85),
        (r"\b(?:try|use|get|start\s+with)\s+\w+\s+(?:first|today|now)\b", 0.9),
        (r"\b(?:my|our)\s+(?:recommendation|top\s+pick)\s+(?:is|would\s+be)\b", 1.0),
        (r"\b(?:hands\s+down|without\s+a\s+doubt)\b", 0.9),
        (r"\b(?:can't\s+go\s+wrong\s+with)\b", 0.9),
        (r"\b(?:i\s+would|i'd)\s+(?:suggest|recommend|go\s+with)\b", 0.95),
        (r"\b(?:the\s+)?(?:best|top|#1|number\s+one)\s+(?:is|solution|tool)\b", 0.85),
    ]

    # Patterns for TRUSTED state
    # Brand cited as authority without sales push
    TRUSTED_PATTERNS = [
        (r"\b(?:trusted|reliable|reputable)\b", 0.9),
        (r"\b(?:industry|market)\s+(?:leader|standard)\b", 0.95),
        (r"\b(?:well-known|established|proven)\b", 0.85),
        (r"\b(?:widely\s+(?:used|adopted|recognized))\b", 0.9),
        (r"\btrusted\s+by\s+(?:millions|thousands|many|companies)\b", 0.95),
        (r"\b(?:gold\s+standard|benchmark)\b", 0.9),
        (r"\b(?:industry-leading|leading)\b", 0.85),
        (r"\b(?:has|with)\s+(?:a\s+)?(?:solid|strong|excellent)\s+(?:reputation|track\s+record)\b", 0.9),
        (r"\b(?:backed\s+by|supported\s+by)\b", 0.8),
        (r"\b(?:enterprise-grade|enterprise-ready)\b", 0.85),
        (r"\b(?:certified|accredited)\b", 0.8),
    ]

    # Patterns for COMPARED state
    # Brand in neutral evaluation context
    COMPARED_PATTERNS = [
        (r"\b(?:compared\s+to|in\s+comparison\s+to)\b", 0.95),
        (r"\bvs\.?\s+\w+\b", 0.9),
        (r"\bversus\b", 0.9),
        (r"\b(?:unlike|similar\s+to)\b", 0.8),
        (r"\b(?:alternative\s+to|alternatives?\s+(?:include|are))\b", 0.85),
        (r"\b(?:pros\s+and\s+cons|advantages\s+and\s+disadvantages)\b", 0.9),
        (r"\b(?:both\s+\w+\s+and\s+\w+|either\s+\w+\s+or)\b", 0.7),
        (r"\b(?:on\s+(?:the\s+)?one\s+hand|on\s+the\s+other\s+hand)\b", 0.85),
        (r"\b(?:while|whereas)\s+\w+\b", 0.7),
        (r"\b(?:differs?\s+from|different\s+from)\b", 0.8),
        (r"\b(?:comparison|comparing)\b", 0.85),
        (r"\b(?:head-to-head|side-by-side)\b", 0.9),
    ]

    # Patterns for MENTIONED state
    # Brand name appears but without special context
    MENTIONED_PATTERNS = [
        (r"\b(?:such\s+as|like|including)\b", 0.6),
        (r"\b(?:for\s+example|for\s+instance|e\.g\.)\b", 0.6),
        (r"\b(?:options?\s+(?:include|are)|choices?\s+(?:include|are))\b", 0.7),
        (r"\b(?:popular|common|available)\b", 0.5),
        (r"\b(?:also|another|other)\b", 0.4),
        (r"\b(?:there\s+(?:is|are)|you\s+(?:can|could|might))\b", 0.4),
    ]

    def __init__(self, context_window: int = 150):
        """
        Initialize the pattern matcher.

        Args:
            context_window: Characters of context to analyze around brand mentions.
        """
        self.context_window = context_window

        # Compile patterns
        self._compiled_patterns = {
            BrandPresenceState.RECOMMENDED: self._compile_patterns(self.RECOMMENDED_PATTERNS),
            BrandPresenceState.TRUSTED: self._compile_patterns(self.TRUSTED_PATTERNS),
            BrandPresenceState.COMPARED: self._compile_patterns(self.COMPARED_PATTERNS),
            BrandPresenceState.MENTIONED: self._compile_patterns(self.MENTIONED_PATTERNS),
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

    def find_brand_context(
        self,
        text: str,
        brand_name: str,
    ) -> list[tuple[int, str]]:
        """
        Find all occurrences of a brand and extract context.

        Args:
            text: Full text to search.
            brand_name: Brand name to find.

        Returns:
            List of (position, context) tuples.
        """
        contexts = []
        text_lower = text.lower()
        brand_lower = brand_name.lower()

        pos = 0
        while True:
            pos = text_lower.find(brand_lower, pos)
            if pos == -1:
                break

            # Extract context around the mention
            start = max(0, pos - self.context_window)
            end = min(len(text), pos + len(brand_name) + self.context_window)
            context = text[start:end]

            contexts.append((pos, context))
            pos += 1

        return contexts

    def classify_presence(
        self,
        context: str,
        brand_name: str,
    ) -> tuple[BrandPresenceState, float, list[str]]:
        """
        Classify the presence state based on context.

        Implements "one dominant state per brand per answer" rule.
        Priority order: RECOMMENDED > TRUSTED > COMPARED > MENTIONED > IGNORED

        Args:
            context: Text context around the brand mention.
            brand_name: The brand name.

        Returns:
            Tuple of (presence_state, confidence, signals).
        """
        signals = []
        scores = {
            BrandPresenceState.RECOMMENDED: 0.0,
            BrandPresenceState.TRUSTED: 0.0,
            BrandPresenceState.COMPARED: 0.0,
            BrandPresenceState.MENTIONED: 0.0,
        }

        # Check each presence type
        for presence, patterns in self._compiled_patterns.items():
            for pattern, weight in patterns:
                if pattern.search(context):
                    scores[presence] += weight
                    signals.append(f"{presence.value}:{pattern.pattern[:30]}")

        # Find the dominant state (highest score)
        max_score = 0.0
        dominant = BrandPresenceState.MENTIONED  # Default

        # Priority order for tie-breaking
        priority_order = [
            BrandPresenceState.RECOMMENDED,
            BrandPresenceState.TRUSTED,
            BrandPresenceState.COMPARED,
            BrandPresenceState.MENTIONED,
        ]

        for presence in priority_order:
            if scores[presence] > max_score:
                max_score = scores[presence]
                dominant = presence

        # If no patterns matched, it's just mentioned
        if max_score == 0:
            dominant = BrandPresenceState.MENTIONED
            max_score = 0.5

        # Normalize confidence
        confidence = min(1.0, max_score / 2.0) if max_score > 0 else 0.5

        return dominant, confidence, signals[:5]  # Limit signals

    def get_position_rank(
        self,
        text: str,
        brand_name: str,
        all_brands: list[str],
    ) -> int | None:
        """
        Get the position rank of a brand among all brands.

        Args:
            text: Full response text.
            brand_name: Brand to get rank for.
            all_brands: List of all brands found.

        Returns:
            Position rank (1 = first mentioned) or None.
        """
        text_lower = text.lower()
        positions = []

        for brand in all_brands:
            pos = text_lower.find(brand.lower())
            if pos >= 0:
                positions.append((pos, brand))

        # Sort by position
        positions.sort(key=lambda x: x[0])

        # Find rank of target brand
        for rank, (pos, brand) in enumerate(positions, start=1):
            if brand.lower() == brand_name.lower():
                return rank

        return None
