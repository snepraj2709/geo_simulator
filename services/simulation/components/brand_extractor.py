"""
Brand Extractor.

Extracts brand mentions, presence states, beliefs, and intent rankings
from LLM responses. Uses a combination of pattern matching and LLM-based
analysis for accurate brand detection.
"""

import re
import uuid
from dataclasses import dataclass
from typing import Any

from shared.config import settings
from shared.llm.factory import get_llm_client, LLMProvider
from shared.utils.logging import get_logger

from services.simulation.schemas import (
    BeliefType,
    BrandExtractionResult,
    BrandMention,
    BrandPresenceType,
    IntentRanking,
    LLMProviderType,
    NormalizedLLMResponse,
    QueryIntentType,
)

logger = get_logger(__name__)


# Common brand indicators for pattern matching
BRAND_INDICATORS = [
    r"\b(?:try|use|recommend|consider|check out|look at)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)\b",
    r"\b([A-Z][a-zA-Z0-9]+(?:\.[a-z]{2,4})?)\s+(?:is|offers|provides|has)\b",
    r"\bsuch as\s+([A-Z][a-zA-Z0-9]+(?:,\s*[A-Z][a-zA-Z0-9]+)*)\b",
    r"\b(?:platforms?|tools?|services?|solutions?)\s+like\s+([A-Z][a-zA-Z0-9]+)\b",
]

# Patterns for belief type detection
BELIEF_PATTERNS = {
    BeliefType.SUPERIORITY: [
        r"\bbest\b",
        r"\btop\b",
        r"\bleading\b",
        r"\bsuperior\b",
        r"\bmost popular\b",
        r"\b#1\b",
        r"\bmarket leader\b",
    ],
    BeliefType.SOCIAL_PROOF: [
        r"\bmillions of users\b",
        r"\bwidely used\b",
        r"\bpopular choice\b",
        r"\bmany companies\b",
        r"\btrusted by\b",
        r"\bused by\b",
    ],
    BeliefType.OUTCOME: [
        r"\bincreases?\b",
        r"\bimproves?\b",
        r"\bboosts?\b",
        r"\bsaves?\b",
        r"\bresults?\b",
        r"\bROI\b",
        r"\befficiency\b",
    ],
    BeliefType.TRANSACTION: [
        r"\bfree trial\b",
        r"\bsign up\b",
        r"\bget started\b",
        r"\bpricing\b",
        r"\bsubscribe\b",
        r"\bpurchase\b",
    ],
    BeliefType.IDENTITY: [
        r"\bfor (teams|developers|enterprises|businesses)\b",
        r"\bdesigned for\b",
        r"\bperfect for\b",
        r"\bideal for\b",
    ],
    BeliefType.TRUTH: [
        r"\bin fact\b",
        r"\bactually\b",
        r"\bdata shows\b",
        r"\bstudies indicate\b",
        r"\bobjectively\b",
    ],
}

# Patterns for presence type detection
PRESENCE_PATTERNS = {
    BrandPresenceType.RECOMMENDED: [
        r"\brecommend\b",
        r"\bsuggest\b",
        r"\bhighly recommend\b",
        r"\bshould (?:try|use|consider)\b",
        r"\bbest choice\b",
        r"\btop pick\b",
    ],
    BrandPresenceType.TRUSTED: [
        r"\breliable\b",
        r"\btrusted\b",
        r"\bestablished\b",
        r"\breputable\b",
        r"\bwell-known\b",
        r"\bindustry standard\b",
    ],
    BrandPresenceType.COMPARED: [
        r"\bcompared to\b",
        r"\bversus\b",
        r"\bvs\.?\b",
        r"\balternative to\b",
        r"\bunlike\b",
        r"\bsimilar to\b",
    ],
    BrandPresenceType.MENTIONED: [
        r"\b(?:is|are)\b",
        r"\bincluding\b",
        r"\bsuch as\b",
        r"\blike\b",
    ],
}

# Intent ranking patterns
INTENT_PATTERNS = {
    QueryIntentType.COMMERCIAL: [
        r"\bbuy\b",
        r"\bprice\b",
        r"\bcost\b",
        r"\bpurchase\b",
        r"\bsubscription\b",
        r"\bplan\b",
    ],
    QueryIntentType.INFORMATIONAL: [
        r"\bwhat is\b",
        r"\bhow does\b",
        r"\bexplain\b",
        r"\blearn\b",
        r"\bunderstand\b",
    ],
    QueryIntentType.NAVIGATIONAL: [
        r"\bwebsite\b",
        r"\blogin\b",
        r"\bsign in\b",
        r"\bdashboard\b",
        r"\baccount\b",
    ],
    QueryIntentType.TRANSACTIONAL: [
        r"\bsign up\b",
        r"\bregister\b",
        r"\bdownload\b",
        r"\binstall\b",
        r"\bget started\b",
    ],
}


@dataclass
class ExtractionConfig:
    """Configuration for brand extraction."""

    use_llm_extraction: bool = True
    llm_provider: LLMProvider = LLMProvider.OPENAI
    min_confidence: float = 0.5
    max_brands_per_response: int = 20
    context_window_chars: int = 200


class BrandExtractor:
    """
    Extracts brand information from LLM responses.

    Features:
    - Pattern-based brand detection
    - LLM-powered brand analysis (optional)
    - Presence type classification
    - Belief type detection
    - Intent ranking
    - Contextual framing extraction

    Usage:
        extractor = BrandExtractor()
        result = await extractor.extract(response)
        # or for batch processing
        results = await extractor.extract_batch(responses)
    """

    def __init__(self, config: ExtractionConfig | None = None):
        """
        Initialize the extractor.

        Args:
            config: Extraction configuration.
        """
        self.config = config or ExtractionConfig()
        self._llm_client = None

        # Compile patterns for efficiency
        self._brand_patterns = [re.compile(p, re.IGNORECASE) for p in BRAND_INDICATORS]
        self._belief_patterns = {
            belief: [re.compile(p, re.IGNORECASE) for p in patterns]
            for belief, patterns in BELIEF_PATTERNS.items()
        }
        self._presence_patterns = {
            presence: [re.compile(p, re.IGNORECASE) for p in patterns]
            for presence, patterns in PRESENCE_PATTERNS.items()
        }
        self._intent_patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }

    @property
    def llm_client(self):
        """Get LLM client for advanced extraction."""
        if self._llm_client is None and self.config.use_llm_extraction:
            self._llm_client = get_llm_client(self.config.llm_provider)
        return self._llm_client

    async def extract(
        self,
        response: NormalizedLLMResponse,
        known_brands: list[str] | None = None,
    ) -> BrandExtractionResult:
        """
        Extract brands and metrics from a response.

        Args:
            response: The LLM response to analyze.
            known_brands: Optional list of known brands to look for.

        Returns:
            Brand extraction result.
        """
        text = response.response_text
        brands: list[BrandMention] = []

        # Step 1: Pattern-based extraction
        pattern_brands = self._extract_brands_from_patterns(text)

        # Step 2: Look for known brands
        if known_brands:
            known_found = self._find_known_brands(text, known_brands)
            pattern_brands.update(known_found)

        # Step 3: Analyze each brand mention
        for position, brand_name in enumerate(pattern_brands, start=1):
            if len(brands) >= self.config.max_brands_per_response:
                break

            # Get context around the brand mention
            context = self._get_context(text, brand_name)

            # Determine presence type
            presence = self._determine_presence(context, brand_name)

            # Determine belief type
            belief = self._determine_belief(context)

            brand = BrandMention(
                brand_name=brand_name,
                normalized_name=brand_name.lower().strip(),
                presence=presence,
                position_rank=position,
                belief_sold=belief,
                context_snippet=context[:500],
                confidence=0.8,  # Pattern-based confidence
            )
            brands.append(brand)

        # Step 4: Determine intent ranking
        intent_ranking = self._determine_intent_ranking(text)

        # Step 5: Extract contextual framing
        contextual_framing = self._extract_contextual_framing(brands, text)

        # Step 6: Optional LLM-powered refinement
        if self.config.use_llm_extraction and len(brands) > 0:
            try:
                brands, intent_ranking = await self._refine_with_llm(
                    text, brands, intent_ranking
                )
            except Exception as e:
                logger.warning(
                    "LLM refinement failed, using pattern-based results",
                    error=str(e),
                )

        return BrandExtractionResult(
            response_id=response.id,
            brands=brands,
            intent_ranking=intent_ranking,
            contextual_framing=contextual_framing,
        )

    async def extract_batch(
        self,
        responses: list[NormalizedLLMResponse],
        known_brands: list[str] | None = None,
    ) -> list[BrandExtractionResult]:
        """
        Extract brands from multiple responses.

        Args:
            responses: List of responses to analyze.
            known_brands: Optional list of known brands.

        Returns:
            List of extraction results.
        """
        results = []
        for response in responses:
            result = await self.extract(response, known_brands)
            results.append(result)

            # Update response with extracted brands
            response.brands_mentioned = [b.normalized_name for b in result.brands]

        return results

    def _extract_brands_from_patterns(self, text: str) -> set[str]:
        """Extract brand names using regex patterns."""
        brands = set()

        for pattern in self._brand_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # Clean and validate the match
                cleaned = self._clean_brand_name(match)
                if cleaned and len(cleaned) > 1:
                    brands.add(cleaned)

        # Also look for capitalized words that might be brands
        words = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?\b", text)
        for word in words:
            cleaned = self._clean_brand_name(word)
            if cleaned and len(cleaned) > 2 and not self._is_common_word(cleaned):
                brands.add(cleaned)

        return brands

    def _find_known_brands(self, text: str, known_brands: list[str]) -> set[str]:
        """Find known brands in the text."""
        found = set()
        text_lower = text.lower()

        for brand in known_brands:
            if brand.lower() in text_lower:
                found.add(brand)

        return found

    def _clean_brand_name(self, name: str) -> str:
        """Clean and normalize a brand name."""
        # Remove common suffixes
        name = re.sub(r"\s+(Inc|LLC|Ltd|Corp|Corporation|Company)\.?$", "", name, flags=re.IGNORECASE)
        # Remove punctuation
        name = re.sub(r"[.,;:!?]$", "", name)
        return name.strip()

    def _is_common_word(self, word: str) -> bool:
        """Check if a word is too common to be a brand."""
        common_words = {
            "The", "This", "That", "These", "Those", "Here", "There",
            "However", "Therefore", "Additionally", "Furthermore",
            "First", "Second", "Third", "Finally", "Overall",
            "Many", "Some", "Most", "All", "Each", "Every",
            "When", "While", "Where", "What", "Which", "Who",
            "Also", "Just", "Only", "Even", "Still", "Already",
            "Great", "Good", "Best", "Better", "More", "Less",
        }
        return word in common_words

    def _get_context(self, text: str, brand_name: str) -> str:
        """Get text context around a brand mention."""
        window = self.config.context_window_chars
        text_lower = text.lower()
        brand_lower = brand_name.lower()

        pos = text_lower.find(brand_lower)
        if pos == -1:
            return ""

        start = max(0, pos - window)
        end = min(len(text), pos + len(brand_name) + window)

        return text[start:end]

    def _determine_presence(self, context: str, brand_name: str) -> BrandPresenceType:
        """Determine the presence type of a brand mention."""
        # Check patterns in order of specificity
        for presence, patterns in self._presence_patterns.items():
            for pattern in patterns:
                if pattern.search(context):
                    return presence

        return BrandPresenceType.MENTIONED

    def _determine_belief(self, context: str) -> BeliefType | None:
        """Determine the belief type installed by a brand mention."""
        max_matches = 0
        best_belief = None

        for belief, patterns in self._belief_patterns.items():
            matches = sum(1 for p in patterns if p.search(context))
            if matches > max_matches:
                max_matches = matches
                best_belief = belief

        return best_belief

    def _determine_intent_ranking(self, text: str) -> IntentRanking | None:
        """Determine the intent ranking of the response."""
        max_matches = 0
        best_intent = None

        for intent, patterns in self._intent_patterns.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches > max_matches:
                max_matches = matches
                best_intent = intent

        if best_intent is None:
            return None

        # Calculate confidence based on number of matches
        total_patterns = sum(len(p) for p in self._intent_patterns.values())
        confidence = min(1.0, max_matches / (total_patterns / 4))

        return IntentRanking(
            query_intent=best_intent,
            confidence=confidence,
        )

    def _extract_contextual_framing(
        self,
        brands: list[BrandMention],
        text: str,
    ) -> dict[str, str]:
        """Extract contextual framing for each brand."""
        framing = {}

        for brand in brands:
            context = brand.context_snippet

            # Extract a short framing description
            if brand.presence == BrandPresenceType.RECOMMENDED:
                framing[brand.brand_name] = "Recommended solution"
            elif brand.presence == BrandPresenceType.TRUSTED:
                framing[brand.brand_name] = "Trusted/established option"
            elif brand.presence == BrandPresenceType.COMPARED:
                framing[brand.brand_name] = "Compared alternative"
            else:
                framing[brand.brand_name] = "Mentioned in context"

        return framing

    async def _refine_with_llm(
        self,
        text: str,
        brands: list[BrandMention],
        intent_ranking: IntentRanking | None,
    ) -> tuple[list[BrandMention], IntentRanking | None]:
        """Use LLM to refine extraction results."""
        if not self.llm_client:
            return brands, intent_ranking

        # Build prompt for refinement
        brand_names = [b.brand_name for b in brands]
        prompt = f"""Analyze this text and verify the brand mentions. Return JSON with:
1. "verified_brands": list of actual brand/company names from [{', '.join(brand_names)}]
2. "intent": one of [Commercial, Informational, Navigational, Transactional]

Text: {text[:1500]}

Return only valid JSON."""

        try:
            response = await self.llm_client.complete_json(prompt)
            data = response.get_json()

            if isinstance(data, dict):
                # Filter brands to only verified ones
                verified = set(data.get("verified_brands", []))
                brands = [b for b in brands if b.brand_name in verified]

                # Update intent if provided
                intent_str = data.get("intent")
                if intent_str:
                    try:
                        intent = QueryIntentType(intent_str)
                        intent_ranking = IntentRanking(
                            query_intent=intent,
                            confidence=0.9,
                        )
                    except ValueError:
                        pass

        except Exception as e:
            logger.debug(
                "LLM refinement parsing failed",
                error=str(e),
            )

        return brands, intent_ranking

    def get_extraction_stats(self) -> dict[str, Any]:
        """Get extraction statistics."""
        return {
            "use_llm_extraction": self.config.use_llm_extraction,
            "min_confidence": self.config.min_confidence,
            "max_brands_per_response": self.config.max_brands_per_response,
        }
