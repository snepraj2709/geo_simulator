"""
Brand Presence Classifier.

Main classification engine that orchestrates brand detection,
presence state classification, and belief type detection.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from shared.utils.logging import get_logger

from services.brand_detector.schemas import (
    BeliefType,
    BrandPresenceState,
    BrandPresenceResult,
    BrandDetectionResponse,
)
from services.brand_detector.components.pattern_matcher import PresencePatternMatcher
from services.brand_detector.components.belief_detector import BeliefTypeDetector

logger = get_logger(__name__)


@dataclass
class ClassifierConfig:
    """Configuration for the brand presence classifier."""

    # Context window for brand analysis
    context_window: int = 150

    # Minimum confidence threshold (lowered to include mentioned brands)
    min_confidence: float = 0.2

    # Maximum brands to process per response
    max_brands: int = 50

    # Whether to use NER if available
    use_ner: bool = True


@dataclass
class BrandCandidate:
    """A candidate brand found in text."""

    name: str
    normalized_name: str
    position: int
    context: str
    source: str = "regex"  # regex, ner, known


class BrandPresenceClassifier:
    """
    Main brand presence classification engine.

    Implements the Brand Presence Detector from ARCHITECTURE.md:
    - Analyzes LLM responses to determine brand positioning state
    - Classifies brands into: ignored, mentioned, trusted, recommended, compared
    - Enforces "one dominant state per brand per answer" rule
    - Detects belief types for each brand mention
    """

    # Patterns to find brand mentions
    BRAND_DETECTION_PATTERNS = [
        # Brand recommendations
        r"\b(?:try|use|recommend|consider|check\s+out)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)\b",
        # Brand as subject
        r"\b([A-Z][a-zA-Z0-9]+(?:\.[a-z]{2,4})?)\s+(?:is|offers|provides|has|delivers)\b",
        # Lists of brands
        r"\b(?:such\s+as|like|including)\s+([A-Z][a-zA-Z0-9]+(?:,\s*[A-Z][a-zA-Z0-9]+)*)\b",
        # Platform/tool mentions
        r"\b(?:platforms?|tools?|services?|solutions?)\s+like\s+([A-Z][a-zA-Z0-9]+)\b",
        # Comparison patterns
        r"\b([A-Z][a-zA-Z0-9]+)\s+(?:vs\.?|versus|compared\s+to)\b",
        # Product names with common suffixes
        r"\b([A-Z][a-zA-Z0-9]+(?:Pro|Plus|Enterprise|Cloud|AI|HQ|\.io|\.com))\b",
    ]

    # Common non-brand words to filter
    COMMON_WORDS = {
        "The", "This", "That", "These", "Those", "Here", "There",
        "However", "Therefore", "Additionally", "Furthermore",
        "First", "Second", "Third", "Finally", "Overall",
        "Many", "Some", "Most", "All", "Each", "Every",
        "When", "While", "Where", "What", "Which", "Who",
        "Also", "Just", "Only", "Even", "Still", "Already",
        "Great", "Good", "Best", "Better", "More", "Less",
        "Using", "Getting", "Making", "Building", "Creating",
        "For", "With", "From", "Into", "About", "Through",
        "It", "They", "We", "You", "I", "He", "She",
        "And", "But", "Or", "So", "If", "Then",
        "Is", "Are", "Was", "Were", "Be", "Been",
        "Has", "Have", "Had", "Do", "Does", "Did",
        "Can", "Could", "Would", "Should", "May", "Might",
        "One", "Two", "Three", "Four", "Five",
        "New", "Old", "Other", "Another", "Next", "Last",
        "Note", "Please", "See", "Look", "Check",
        "Step", "Steps", "Way", "Ways", "Example", "Examples",
    }

    def __init__(self, config: ClassifierConfig | None = None):
        """
        Initialize the classifier.

        Args:
            config: Classifier configuration.
        """
        self.config = config or ClassifierConfig()

        # Initialize sub-components
        self.pattern_matcher = PresencePatternMatcher(
            context_window=self.config.context_window
        )
        self.belief_detector = BeliefTypeDetector()

        # Compile brand detection patterns
        self._brand_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.BRAND_DETECTION_PATTERNS
        ]

    def detect_brands(
        self,
        text: str,
        known_brands: list[str] | None = None,
        tracked_brand: str | None = None,
    ) -> BrandDetectionResponse:
        """
        Detect brands and their presence states in text.

        Args:
            text: LLM response text to analyze.
            known_brands: Optional list of known brand names to look for.
            tracked_brand: The user's own brand to specifically track.

        Returns:
            BrandDetectionResponse with all detected brands.
        """
        if not text:
            return BrandDetectionResponse(
                brands=[],
                total_brands_found=0,
            )

        # Step 1: Find brand candidates
        candidates = self._find_brand_candidates(text, known_brands, tracked_brand)

        if not candidates:
            # Check if tracked brand exists but was ignored
            if tracked_brand:
                return BrandDetectionResponse(
                    brands=[],
                    tracked_brand_result=BrandPresenceResult(
                        brand_name=tracked_brand,
                        normalized_name=tracked_brand.lower().strip(),
                        presence=BrandPresenceState.IGNORED,
                        position_rank=None,
                        confidence=1.0,
                        detection_signals=["not_mentioned"],
                    ),
                    total_brands_found=0,
                )
            return BrandDetectionResponse(brands=[], total_brands_found=0)

        # Step 2: Classify each brand
        all_brand_names = [c.name for c in candidates]
        results = []

        for candidate in candidates[:self.config.max_brands]:
            result = self._classify_brand(text, candidate, all_brand_names)
            if result.confidence >= self.config.min_confidence:
                results.append(result)

        # Sort by position rank
        results.sort(key=lambda x: x.position_rank or 999)

        # Find tracked brand result
        tracked_result = None
        if tracked_brand:
            tracked_normalized = tracked_brand.lower().strip()
            tracked_result = next(
                (r for r in results if r.normalized_name == tracked_normalized),
                None
            )
            if not tracked_result:
                # Brand was ignored
                tracked_result = BrandPresenceResult(
                    brand_name=tracked_brand,
                    normalized_name=tracked_normalized,
                    presence=BrandPresenceState.IGNORED,
                    position_rank=None,
                    confidence=1.0,
                    detection_signals=["not_mentioned"],
                )

        return BrandDetectionResponse(
            brands=results,
            tracked_brand_result=tracked_result,
            total_brands_found=len(results),
            analysis_metadata={
                "candidates_found": len(candidates),
                "brands_classified": len(results),
            },
        )

    def _find_brand_candidates(
        self,
        text: str,
        known_brands: list[str] | None,
        tracked_brand: str | None,
    ) -> list[BrandCandidate]:
        """Find brand candidates in text."""
        candidates = {}  # normalized_name -> candidate

        # First, look for known brands
        if known_brands:
            for brand in known_brands:
                self._add_known_brand(text, brand, candidates)

        if tracked_brand:
            self._add_known_brand(text, tracked_brand, candidates)

        # Then use regex patterns
        self._find_brands_with_patterns(text, candidates)

        # Also find capitalized words that might be brands
        self._find_capitalized_brands(text, candidates)

        return list(candidates.values())

    def _add_known_brand(
        self,
        text: str,
        brand: str,
        candidates: dict[str, BrandCandidate],
    ) -> None:
        """Add a known brand if found in text."""
        text_lower = text.lower()
        brand_lower = brand.lower()
        normalized = brand_lower.strip()

        if normalized in candidates:
            return

        pos = text_lower.find(brand_lower)
        if pos >= 0:
            context = self._get_context(text, pos, len(brand))
            candidates[normalized] = BrandCandidate(
                name=brand,
                normalized_name=normalized,
                position=pos,
                context=context,
                source="known",
            )

    def _find_brands_with_patterns(
        self,
        text: str,
        candidates: dict[str, BrandCandidate],
    ) -> None:
        """Find brands using regex patterns."""
        for pattern in self._brand_patterns:
            for match in pattern.finditer(text):
                brand_text = match.group(1) if match.lastindex else match.group(0)

                # Handle comma-separated lists
                if "," in brand_text:
                    for part in brand_text.split(","):
                        self._process_brand_match(text, part.strip(), match.start(), candidates)
                else:
                    self._process_brand_match(text, brand_text, match.start(), candidates)

    def _process_brand_match(
        self,
        text: str,
        brand_text: str,
        pos: int,
        candidates: dict[str, BrandCandidate],
    ) -> None:
        """Process a potential brand match."""
        cleaned = self._clean_brand_name(brand_text)
        if not self._is_valid_brand(cleaned):
            return

        normalized = cleaned.lower().strip()
        if normalized in candidates:
            return

        context = self._get_context(text, pos, len(cleaned))
        candidates[normalized] = BrandCandidate(
            name=cleaned,
            normalized_name=normalized,
            position=pos,
            context=context,
            source="regex",
        )

    def _find_capitalized_brands(
        self,
        text: str,
        candidates: dict[str, BrandCandidate],
    ) -> None:
        """Find capitalized words that might be brands."""
        # Pattern for capitalized words/phrases
        pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")

        for match in pattern.finditer(text):
            word = match.group(1)
            cleaned = self._clean_brand_name(word)

            if not self._is_valid_brand(cleaned):
                continue

            normalized = cleaned.lower().strip()
            if normalized in candidates:
                continue

            context = self._get_context(text, match.start(), len(cleaned))
            candidates[normalized] = BrandCandidate(
                name=cleaned,
                normalized_name=normalized,
                position=match.start(),
                context=context,
                source="capitalized",
            )

    def _classify_brand(
        self,
        text: str,
        candidate: BrandCandidate,
        all_brands: list[str],
    ) -> BrandPresenceResult:
        """
        Classify a brand's presence state.

        Implements "one dominant state per brand per answer" rule.
        """
        # Get all contexts for this brand
        contexts = self.pattern_matcher.find_brand_context(text, candidate.name)

        if not contexts:
            contexts = [(candidate.position, candidate.context)]

        # Aggregate signals from all contexts
        all_signals = []
        presence_scores = {}

        for pos, context in contexts:
            presence, conf, signals = self.pattern_matcher.classify_presence(
                context, candidate.name
            )
            presence_scores[presence] = presence_scores.get(presence, 0) + conf
            all_signals.extend(signals)

        # Determine dominant presence (highest score)
        dominant_presence = max(presence_scores, key=presence_scores.get)
        confidence = min(1.0, presence_scores[dominant_presence] / len(contexts))

        # Get position rank
        position_rank = self.pattern_matcher.get_position_rank(
            text, candidate.name, all_brands
        )

        # Detect belief type from combined contexts
        combined_context = " ".join([c for _, c in contexts])
        belief_type, belief_conf, belief_signals = self.belief_detector.detect_belief(
            combined_context
        )
        all_signals.extend(belief_signals)

        return BrandPresenceResult(
            brand_name=candidate.name,
            normalized_name=candidate.normalized_name,
            presence=dominant_presence,
            position_rank=position_rank,
            belief_sold=belief_type,
            confidence=confidence,
            context_snippet=contexts[0][1][:500] if contexts else None,
            detection_signals=list(set(all_signals))[:10],
        )

    def _get_context(self, text: str, pos: int, brand_len: int) -> str:
        """Get context around a position."""
        window = self.config.context_window
        start = max(0, pos - window)
        end = min(len(text), pos + brand_len + window)
        return text[start:end]

    def _clean_brand_name(self, name: str) -> str:
        """Clean and normalize a brand name."""
        # Remove common suffixes
        name = re.sub(
            r"\s+(?:Inc|LLC|Ltd|Corp|Corporation|Company|Co|Group)\.?$",
            "", name, flags=re.IGNORECASE
        )
        # Remove trailing punctuation
        name = re.sub(r"[.,;:!?]+$", "", name)
        return name.strip()

    def _is_valid_brand(self, name: str) -> bool:
        """Check if a name is likely a valid brand."""
        if not name or len(name) < 2:
            return False

        if name in self.COMMON_WORDS:
            return False

        # Must have at least one letter
        if not any(c.isalpha() for c in name):
            return False

        # Must start with capital letter for brand detection
        if not name[0].isupper():
            return False

        return True

    def classify_for_llm_response(
        self,
        llm_response_id: uuid.UUID,
        response_text: str,
        known_brands: list[str] | None = None,
        tracked_brand: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Classify brands for storage as LLMBrandState records.

        Returns data ready for database insertion.
        """
        detection = self.detect_brands(
            response_text,
            known_brands=known_brands,
            tracked_brand=tracked_brand,
        )

        records = []
        for brand in detection.brands:
            records.append({
                "llm_response_id": llm_response_id,
                "brand_name": brand.brand_name,
                "normalized_name": brand.normalized_name,
                "presence": brand.presence.value,
                "position_rank": brand.position_rank,
                "belief_sold": brand.belief_sold.value if brand.belief_sold else None,
                "confidence": brand.confidence,
            })

        return records
