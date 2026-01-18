"""
Advanced Analysis Components for Simulation Service.

Provides enhanced brand extraction, intent ranking, priority detection,
and contextual framing analysis with NER integration.
"""

import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from shared.utils.logging import get_logger

# Import NER extractor from scraper service
try:
    from services.scraper.components.ner_extractor import (
        NERExtractor,
        ExtractedNamedEntities,
        NamedEntity,
    )
    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False

logger = get_logger(__name__)


# ==================== Enums ====================


class FramingType(str, Enum):
    """Types of contextual framing for brand mentions."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    COMPARATIVE = "comparative"
    AUTHORITATIVE = "authoritative"
    CAUTIONARY = "cautionary"


class PrioritySignal(str, Enum):
    """Types of priority signals in brand positioning."""

    FIRST_MENTION = "first_mention"
    HEADER_PLACEMENT = "header_placement"
    RECOMMENDATION = "recommendation"
    COMPARISON_WINNER = "comparison_winner"
    FEATURED_EXAMPLE = "featured_example"
    CONCLUSION_MENTION = "conclusion_mention"


# ==================== Data Classes ====================


@dataclass
class NERBrandMatch:
    """Brand match from NER extraction."""

    text: str
    normalized_name: str
    entity_type: str
    start_pos: int
    end_pos: int
    confidence: float
    source: str = "ner"
    related_entities: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PriorityAnalysis:
    """Priority order analysis for a brand mention."""

    brand_name: str
    mention_rank: int
    first_position: int
    total_mentions: int
    priority_signals: list[PrioritySignal] = field(default_factory=list)
    signal_scores: dict[str, float] = field(default_factory=dict)
    overall_priority_score: float = 0.0


@dataclass
class FramingAnalysis:
    """Contextual framing analysis for a brand mention."""

    brand_name: str
    framing_type: FramingType
    framing_score: float  # -1.0 to 1.0
    context_snippet: str
    framing_indicators: list[str] = field(default_factory=list)
    sentiment_words: list[str] = field(default_factory=list)


@dataclass
class IntentAnalysisResult:
    """Detailed intent analysis result."""

    primary_intent: str
    secondary_intent: str | None
    confidence: float
    intent_scores: dict[str, float] = field(default_factory=dict)
    buying_signals: list[dict[str, Any]] = field(default_factory=list)
    trust_indicators: list[dict[str, Any]] = field(default_factory=list)
    funnel_stage: str | None = None
    query_type: str | None = None


@dataclass
class EnhancedBrandExtraction:
    """Enhanced brand extraction result with NER and analysis."""

    brand_name: str
    normalized_name: str
    extraction_method: str  # regex, ner, llm, combined
    confidence: float
    position_in_response: int
    mention_rank: int
    mention_count: int
    context_snippet: str
    ner_entities: list[dict[str, Any]] = field(default_factory=list)
    priority_analysis: PriorityAnalysis | None = None
    framing_analysis: FramingAnalysis | None = None


# ==================== Enhanced Brand Extractor with NER ====================


class EnhancedBrandExtractor:
    """
    Enhanced brand extraction using regex + NER.

    Combines pattern matching with Named Entity Recognition for
    more accurate brand detection and entity relationship mapping.
    """

    # Brand indicator patterns
    BRAND_PATTERNS = [
        # Direct recommendations
        r"\b(?:try|use|recommend|consider|check out|look at)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)\b",
        # Provider/platform mentions
        r"\b([A-Z][a-zA-Z0-9]+(?:\.[a-z]{2,4})?)\s+(?:is|offers|provides|has)\b",
        # List patterns
        r"\bsuch as\s+([A-Z][a-zA-Z0-9]+(?:,\s*[A-Z][a-zA-Z0-9]+)*)\b",
        r"\b(?:platforms?|tools?|services?|solutions?)\s+like\s+([A-Z][a-zA-Z0-9]+)\b",
        # Comparison patterns
        r"\b([A-Z][a-zA-Z0-9]+)\s+(?:vs\.?|versus|compared to|alternative to)\b",
        # Product/company names with suffixes
        r"\b([A-Z][a-zA-Z0-9]+(?:Pro|Plus|Enterprise|Cloud|AI|HQ))\b",
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
    }

    def __init__(self, use_ner: bool = True, context_window: int = 200):
        """
        Initialize enhanced brand extractor.

        Args:
            use_ner: Whether to use NER for extraction.
            context_window: Characters of context around mentions.
        """
        self.use_ner = use_ner and NER_AVAILABLE
        self.context_window = context_window
        self._ner_extractor = None

        # Compile regex patterns
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.BRAND_PATTERNS
        ]

        if self.use_ner:
            self._ner_extractor = NERExtractor(use_spacy=True)

    def extract_brands(
        self,
        text: str,
        known_brands: list[str] | None = None,
    ) -> list[EnhancedBrandExtraction]:
        """
        Extract brands using combined regex + NER approach.

        Args:
            text: Text to analyze.
            known_brands: Optional list of known brand names.

        Returns:
            List of enhanced brand extractions.
        """
        if not text:
            return []

        # Step 1: Regex-based extraction
        regex_brands = self._extract_with_regex(text)

        # Step 2: NER-based extraction
        ner_brands = {}
        ner_entities = {}
        if self.use_ner and self._ner_extractor:
            ner_brands, ner_entities = self._extract_with_ner(text)

        # Step 3: Known brand matching
        known_matches = {}
        if known_brands:
            known_matches = self._find_known_brands(text, known_brands)

        # Step 4: Combine and deduplicate
        all_brands = self._combine_extractions(
            regex_brands, ner_brands, known_matches, ner_entities
        )

        # Step 5: Analyze positions and build results
        results = self._build_extraction_results(text, all_brands, ner_entities)

        return results

    def _extract_with_regex(self, text: str) -> dict[str, dict[str, Any]]:
        """Extract brands using regex patterns."""
        brands = {}

        for pattern in self._compiled_patterns:
            for match in pattern.finditer(text):
                brand_text = match.group(1) if match.lastindex else match.group(0)

                # Handle comma-separated lists
                if "," in brand_text:
                    for part in brand_text.split(","):
                        cleaned = self._clean_brand_name(part.strip())
                        if cleaned and self._is_valid_brand(cleaned):
                            self._add_brand(brands, cleaned, match.start(), "regex")
                else:
                    cleaned = self._clean_brand_name(brand_text)
                    if cleaned and self._is_valid_brand(cleaned):
                        self._add_brand(brands, cleaned, match.start(), "regex")

        # Also find capitalized multi-word names
        cap_pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")
        for match in cap_pattern.finditer(text):
            word = match.group(1)
            cleaned = self._clean_brand_name(word)
            if cleaned and self._is_valid_brand(cleaned) and len(cleaned) > 2:
                self._add_brand(brands, cleaned, match.start(), "regex")

        return brands

    def _extract_with_ner(
        self,
        text: str,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, list[NamedEntity]]]:
        """Extract brands using NER."""
        brands = {}
        entity_map = {}

        try:
            entities = self._ner_extractor.extract(text)

            # Organizations are primary brand candidates
            for entity in entities.organizations:
                cleaned = self._clean_brand_name(entity.text)
                if cleaned and len(cleaned) > 1:
                    self._add_brand(
                        brands, cleaned, entity.start, "ner",
                        confidence=entity.confidence
                    )

                    # Store entity for later reference
                    normalized = cleaned.lower().strip()
                    if normalized not in entity_map:
                        entity_map[normalized] = []
                    entity_map[normalized].append(entity)

            # Products can also be brands
            for entity in entities.products:
                cleaned = self._clean_brand_name(entity.text)
                if cleaned and len(cleaned) > 1:
                    self._add_brand(
                        brands, cleaned, entity.start, "ner",
                        confidence=entity.confidence * 0.8  # Lower confidence for products
                    )

        except Exception as e:
            logger.warning("NER extraction failed: %s", e)

        return brands, entity_map

    def _find_known_brands(
        self,
        text: str,
        known_brands: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Find known brands in text."""
        brands = {}
        text_lower = text.lower()

        for brand in known_brands:
            brand_lower = brand.lower()
            pos = text_lower.find(brand_lower)

            if pos >= 0:
                self._add_brand(brands, brand, pos, "known", confidence=1.0)

        return brands

    def _add_brand(
        self,
        brands: dict,
        name: str,
        position: int,
        source: str,
        confidence: float = 0.8,
    ) -> None:
        """Add brand to the collection."""
        normalized = name.lower().strip()

        if normalized not in brands:
            brands[normalized] = {
                "name": name,
                "normalized": normalized,
                "positions": [position],
                "sources": {source},
                "confidence": confidence,
            }
        else:
            brands[normalized]["positions"].append(position)
            brands[normalized]["sources"].add(source)
            # Keep highest confidence
            brands[normalized]["confidence"] = max(
                brands[normalized]["confidence"], confidence
            )

    def _combine_extractions(
        self,
        regex_brands: dict,
        ner_brands: dict,
        known_brands: dict,
        ner_entities: dict,
    ) -> dict[str, dict[str, Any]]:
        """Combine extractions from all sources."""
        combined = {}

        # Priority: known > NER > regex
        for normalized, data in known_brands.items():
            combined[normalized] = data
            combined[normalized]["method"] = "known"

        for normalized, data in ner_brands.items():
            if normalized not in combined:
                combined[normalized] = data
                combined[normalized]["method"] = "ner"
            else:
                combined[normalized]["sources"].update(data["sources"])
                combined[normalized]["positions"].extend(data["positions"])

        for normalized, data in regex_brands.items():
            if normalized not in combined:
                combined[normalized] = data
                combined[normalized]["method"] = "regex"
            else:
                combined[normalized]["sources"].update(data["sources"])
                combined[normalized]["positions"].extend(data["positions"])

        # Add NER entities to matching brands
        for normalized, entities in ner_entities.items():
            if normalized in combined:
                combined[normalized]["ner_entities"] = [
                    {"text": e.text, "label": e.label, "confidence": e.confidence}
                    for e in entities
                ]

        return combined

    def _build_extraction_results(
        self,
        text: str,
        brands: dict[str, dict[str, Any]],
        ner_entities: dict,
    ) -> list[EnhancedBrandExtraction]:
        """Build final extraction results with analysis."""
        results = []

        # Sort by first position for ranking
        sorted_brands = sorted(
            brands.items(),
            key=lambda x: min(x[1]["positions"])
        )

        for rank, (normalized, data) in enumerate(sorted_brands, start=1):
            first_pos = min(data["positions"])

            # Get context snippet
            context = self._get_context(text, first_pos, data["name"])

            # Determine extraction method
            sources = data.get("sources", set())
            if "known" in sources:
                method = "known"
            elif "ner" in sources and "regex" in sources:
                method = "combined"
            elif "ner" in sources:
                method = "ner"
            else:
                method = "regex"

            extraction = EnhancedBrandExtraction(
                brand_name=data["name"],
                normalized_name=normalized,
                extraction_method=method,
                confidence=data.get("confidence", 0.8),
                position_in_response=first_pos,
                mention_rank=rank,
                mention_count=len(data["positions"]),
                context_snippet=context,
                ner_entities=data.get("ner_entities", []),
            )

            results.append(extraction)

        return results

    def _get_context(self, text: str, position: int, brand_name: str) -> str:
        """Get context around a brand mention."""
        start = max(0, position - self.context_window)
        end = min(len(text), position + len(brand_name) + self.context_window)
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

        return True


# ==================== Intent Ranking Analyzer ====================


class IntentRankingAnalyzer:
    """
    Sophisticated intent ranking analyzer.

    Analyzes text to determine query intent, buying signals,
    trust indicators, and funnel stage.
    """

    # Intent indicator patterns with weights
    INTENT_PATTERNS = {
        "Commercial": {
            "patterns": [
                (r"\bbuy\b", 1.0),
                (r"\bprice\b", 0.9),
                (r"\bcost\b", 0.8),
                (r"\bpurchase\b", 1.0),
                (r"\bsubscription\b", 0.9),
                (r"\bplan\b", 0.7),
                (r"\bpricing\b", 1.0),
                (r"\bdiscount\b", 0.8),
                (r"\bfree trial\b", 0.9),
                (r"\boffer\b", 0.6),
                (r"\bdeal\b", 0.8),
                (r"\bsale\b", 0.7),
            ],
            "weight": 1.0,
        },
        "Informational": {
            "patterns": [
                (r"\bwhat is\b", 1.0),
                (r"\bhow does\b", 0.9),
                (r"\bhow to\b", 0.9),
                (r"\bexplain\b", 0.8),
                (r"\blearn\b", 0.7),
                (r"\bunderstand\b", 0.8),
                (r"\bguide\b", 0.7),
                (r"\btutorial\b", 0.8),
                (r"\bdefinition\b", 0.9),
                (r"\bwhy\b", 0.6),
                (r"\bbenefits\b", 0.5),
            ],
            "weight": 0.8,
        },
        "Transactional": {
            "patterns": [
                (r"\bsign up\b", 1.0),
                (r"\bregister\b", 0.9),
                (r"\bdownload\b", 0.8),
                (r"\binstall\b", 0.8),
                (r"\bget started\b", 0.9),
                (r"\bstart free\b", 1.0),
                (r"\bcreate account\b", 0.9),
                (r"\bsubscribe\b", 0.8),
                (r"\bbook\b", 0.7),
                (r"\bschedule\b", 0.6),
            ],
            "weight": 0.9,
        },
        "Navigational": {
            "patterns": [
                (r"\bwebsite\b", 0.7),
                (r"\blogin\b", 0.9),
                (r"\bsign in\b", 0.9),
                (r"\bdashboard\b", 0.8),
                (r"\baccount\b", 0.6),
                (r"\bportal\b", 0.7),
                (r"\bhomepage\b", 0.8),
                (r"\bofficial\b", 0.7),
            ],
            "weight": 0.7,
        },
    }

    # Buying signal patterns
    BUYING_SIGNALS = [
        (r"\bbest\s+(?:for|option|choice|alternative)\b", "comparison_shopping", 0.8),
        (r"\bshould\s+I\s+(?:buy|use|get|try)\b", "purchase_consideration", 0.9),
        (r"\brecommend(?:ation)?s?\b", "seeking_recommendation", 0.7),
        (r"\bvs\.?\s+\w+\b", "comparing_options", 0.8),
        (r"\balternative\s+to\b", "looking_for_alternatives", 0.8),
        (r"\bworth\s+(?:it|the|buying)\b", "value_assessment", 0.9),
        (r"\bswitch(?:ing)?\s+(?:to|from)\b", "migration_intent", 0.9),
        (r"\breplace\b", "replacement_intent", 0.8),
        (r"\bupgrade\b", "upgrade_intent", 0.7),
    ]

    # Trust indicators
    TRUST_INDICATORS = [
        (r"\breliable\b", "reliability", 0.8),
        (r"\bsecure\b", "security", 0.9),
        (r"\btrusted\b", "trust", 0.9),
        (r"\breputable\b", "reputation", 0.8),
        (r"\breviews?\b", "social_proof", 0.7),
        (r"\brating\b", "social_proof", 0.7),
        (r"\btestimonial\b", "social_proof", 0.8),
        (r"\bcase\s+stud(?:y|ies)\b", "evidence", 0.8),
        (r"\bproven\b", "evidence", 0.7),
        (r"\bsupport\b", "support_availability", 0.6),
        (r"\bguarantee\b", "risk_reduction", 0.9),
        (r"\bwarranty\b", "risk_reduction", 0.8),
        (r"\brefund\b", "risk_reduction", 0.8),
    ]

    # Funnel stage patterns
    FUNNEL_PATTERNS = {
        "awareness": [
            r"\bwhat\s+is\b",
            r"\bintroduction\b",
            r"\boverview\b",
            r"\bexplain\b",
            r"\bbasics?\b",
        ],
        "consideration": [
            r"\bcompare\b",
            r"\bvs\.?\b",
            r"\breview\b",
            r"\balternative\b",
            r"\bbest\b",
            r"\bdifference\b",
            r"\bpros\s+and\s+cons\b",
        ],
        "purchase": [
            r"\bpricing\b",
            r"\bcost\b",
            r"\bbuy\b",
            r"\bplan\b",
            r"\bsubscribe\b",
            r"\bfree\s+trial\b",
            r"\bdemo\b",
            r"\bquote\b",
        ],
    }

    def __init__(self):
        """Initialize the intent ranking analyzer."""
        # Compile all patterns
        self._compiled_intent = {
            intent: {
                "patterns": [(re.compile(p, re.IGNORECASE), w) for p, w in data["patterns"]],
                "weight": data["weight"],
            }
            for intent, data in self.INTENT_PATTERNS.items()
        }

        self._compiled_buying = [
            (re.compile(p, re.IGNORECASE), signal, weight)
            for p, signal, weight in self.BUYING_SIGNALS
        ]

        self._compiled_trust = [
            (re.compile(p, re.IGNORECASE), indicator, weight)
            for p, indicator, weight in self.TRUST_INDICATORS
        ]

        self._compiled_funnel = {
            stage: [re.compile(p, re.IGNORECASE) for p in patterns]
            for stage, patterns in self.FUNNEL_PATTERNS.items()
        }

    def analyze(self, text: str, prompt_text: str | None = None) -> IntentAnalysisResult:
        """
        Analyze intent from response and optionally prompt text.

        Args:
            text: Response text to analyze.
            prompt_text: Optional original prompt for context.

        Returns:
            Detailed intent analysis result.
        """
        # Combine prompt and response for analysis if available
        full_text = text
        if prompt_text:
            full_text = f"{prompt_text} {text}"

        # Calculate intent scores
        intent_scores = self._calculate_intent_scores(full_text)

        # Find buying signals
        buying_signals = self._find_buying_signals(full_text)

        # Find trust indicators
        trust_indicators = self._find_trust_indicators(full_text)

        # Determine funnel stage
        funnel_stage = self._determine_funnel_stage(full_text)

        # Determine primary and secondary intents
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent = sorted_intents[0][0] if sorted_intents else "Informational"
        secondary_intent = sorted_intents[1][0] if len(sorted_intents) > 1 and sorted_intents[1][1] > 0.3 else None

        # Calculate confidence based on score difference
        primary_score = sorted_intents[0][1] if sorted_intents else 0
        secondary_score = sorted_intents[1][1] if len(sorted_intents) > 1 else 0
        confidence = min(1.0, primary_score * (1 + (primary_score - secondary_score)))

        # Determine query type
        query_type = self._determine_query_type(primary_intent, buying_signals, funnel_stage)

        return IntentAnalysisResult(
            primary_intent=primary_intent,
            secondary_intent=secondary_intent,
            confidence=confidence,
            intent_scores=intent_scores,
            buying_signals=buying_signals,
            trust_indicators=trust_indicators,
            funnel_stage=funnel_stage,
            query_type=query_type,
        )

    def _calculate_intent_scores(self, text: str) -> dict[str, float]:
        """Calculate normalized scores for each intent type."""
        scores = {}
        total_score = 0

        for intent, data in self._compiled_intent.items():
            intent_score = 0
            for pattern, weight in data["patterns"]:
                matches = len(pattern.findall(text))
                intent_score += matches * weight

            scores[intent] = intent_score * data["weight"]
            total_score += scores[intent]

        # Normalize scores
        if total_score > 0:
            scores = {k: v / total_score for k, v in scores.items()}
        else:
            # Default to informational
            scores = {k: 0.0 for k in self.INTENT_PATTERNS}
            scores["Informational"] = 1.0

        return scores

    def _find_buying_signals(self, text: str) -> list[dict[str, Any]]:
        """Find buying signals in text."""
        signals = []

        for pattern, signal_type, weight in self._compiled_buying:
            for match in pattern.finditer(text):
                signals.append({
                    "type": signal_type,
                    "text": match.group(0),
                    "position": match.start(),
                    "weight": weight,
                })

        return signals

    def _find_trust_indicators(self, text: str) -> list[dict[str, Any]]:
        """Find trust indicators in text."""
        indicators = []

        for pattern, indicator_type, weight in self._compiled_trust:
            for match in pattern.finditer(text):
                indicators.append({
                    "type": indicator_type,
                    "text": match.group(0),
                    "position": match.start(),
                    "weight": weight,
                })

        return indicators

    def _determine_funnel_stage(self, text: str) -> str | None:
        """Determine the marketing funnel stage."""
        stage_scores = {}

        for stage, patterns in self._compiled_funnel.items():
            score = sum(len(p.findall(text)) for p in patterns)
            stage_scores[stage] = score

        if not any(stage_scores.values()):
            return None

        return max(stage_scores, key=stage_scores.get)

    def _determine_query_type(
        self,
        primary_intent: str,
        buying_signals: list[dict],
        funnel_stage: str | None,
    ) -> str:
        """Determine the specific query type."""
        if primary_intent == "Commercial":
            if any(s["type"] == "comparison_shopping" for s in buying_signals):
                return "product_comparison"
            elif any(s["type"] == "value_assessment" for s in buying_signals):
                return "value_research"
            return "purchase_research"

        elif primary_intent == "Informational":
            if funnel_stage == "awareness":
                return "exploratory"
            return "educational"

        elif primary_intent == "Transactional":
            if any(s["type"] == "migration_intent" for s in buying_signals):
                return "migration"
            return "conversion"

        elif primary_intent == "Navigational":
            return "direct_navigation"

        return "general"


# ==================== Priority Order Detector ====================


class PriorityOrderDetector:
    """
    Detects priority order and positioning signals for brands.

    Analyzes how brands are positioned in text including:
    - Order of mention
    - Header/section placement
    - Recommendation signals
    - Comparison winner indicators
    """

    # Priority signal patterns
    SIGNAL_PATTERNS = {
        PrioritySignal.RECOMMENDATION: [
            (r"\brecommend\s+(\w+)", 1.0),
            (r"\bsuggest\s+(\w+)", 0.9),
            (r"\btry\s+(\w+)", 0.8),
            (r"\bbest\s+(?:choice|option|pick)\s+is\s+(\w+)", 1.0),
            (r"(?:I|we)\s+(?:would|highly)\s+recommend\s+(\w+)", 1.0),
        ],
        PrioritySignal.COMPARISON_WINNER: [
            (r"(\w+)\s+(?:is|stands)\s+out", 0.9),
            (r"(\w+)\s+(?:wins|leads|excels)", 0.9),
            (r"(?:top|#1|number one)\s+(?:pick|choice)\s+(?:is\s+)?(\w+)", 1.0),
            (r"(\w+)\s+(?:beats|outperforms)", 0.9),
        ],
        PrioritySignal.FEATURED_EXAMPLE: [
            (r"(?:for example|such as|like)\s+(\w+)", 0.7),
            (r"(?:consider|take)\s+(\w+)", 0.6),
            (r"(\w+)\s+is\s+a\s+(?:great|good|popular)\s+example", 0.8),
        ],
    }

    # Header patterns
    HEADER_PATTERNS = [
        r"^#+\s*(\w+)",  # Markdown headers
        r"<h[1-6][^>]*>([^<]+)</h[1-6]>",  # HTML headers
        r"^\*\*(\w+)\*\*",  # Bold text at start of line
    ]

    # Conclusion patterns
    CONCLUSION_PATTERNS = [
        r"(?:in\s+conclusion|overall|finally|to\s+summarize)[,:]?\s+.*?(\w+)",
        r"(?:bottom\s+line|takeaway)[,:]?\s+.*?(\w+)",
    ]

    def __init__(self):
        """Initialize priority order detector."""
        self._compiled_signals = {
            signal: [(re.compile(p, re.IGNORECASE | re.MULTILINE), w) for p, w in patterns]
            for signal, patterns in self.SIGNAL_PATTERNS.items()
        }

        self._compiled_headers = [
            re.compile(p, re.MULTILINE) for p in self.HEADER_PATTERNS
        ]

        self._compiled_conclusions = [
            re.compile(p, re.IGNORECASE) for p in self.CONCLUSION_PATTERNS
        ]

    def analyze(
        self,
        text: str,
        brands: list[EnhancedBrandExtraction],
    ) -> list[PriorityAnalysis]:
        """
        Analyze priority order for each brand.

        Args:
            text: Full response text.
            brands: List of extracted brands.

        Returns:
            Priority analysis for each brand.
        """
        results = []
        brand_names = {b.normalized_name: b for b in brands}

        # Find header mentions
        header_brands = self._find_header_mentions(text, brand_names)

        # Find conclusion mentions
        conclusion_brands = self._find_conclusion_mentions(text, brand_names)

        for brand in brands:
            signals = []
            signal_scores = {}

            # First mention signal
            if brand.mention_rank == 1:
                signals.append(PrioritySignal.FIRST_MENTION)
                signal_scores["first_mention"] = 1.0

            # Header placement
            if brand.normalized_name in header_brands:
                signals.append(PrioritySignal.HEADER_PLACEMENT)
                signal_scores["header_placement"] = header_brands[brand.normalized_name]

            # Conclusion mention
            if brand.normalized_name in conclusion_brands:
                signals.append(PrioritySignal.CONCLUSION_MENTION)
                signal_scores["conclusion_mention"] = 0.8

            # Check for signal patterns
            for signal, patterns in self._compiled_signals.items():
                for pattern, weight in patterns:
                    for match in pattern.finditer(text):
                        matched_name = match.group(1).lower()
                        if matched_name in brand.normalized_name or brand.normalized_name.startswith(matched_name):
                            if signal not in signals:
                                signals.append(signal)
                            signal_scores[signal.value] = max(
                                signal_scores.get(signal.value, 0), weight
                            )

            # Calculate overall priority score
            priority_score = self._calculate_priority_score(brand, signals, signal_scores)

            analysis = PriorityAnalysis(
                brand_name=brand.brand_name,
                mention_rank=brand.mention_rank,
                first_position=brand.position_in_response,
                total_mentions=brand.mention_count,
                priority_signals=signals,
                signal_scores=signal_scores,
                overall_priority_score=priority_score,
            )

            results.append(analysis)

        return results

    def _find_header_mentions(
        self,
        text: str,
        brands: dict[str, EnhancedBrandExtraction],
    ) -> dict[str, float]:
        """Find brands mentioned in headers."""
        header_brands = {}

        for pattern in self._compiled_headers:
            for match in pattern.finditer(text):
                header_text = match.group(1).lower() if match.lastindex else match.group(0).lower()

                for normalized, brand in brands.items():
                    if normalized in header_text or brand.brand_name.lower() in header_text:
                        header_brands[normalized] = 0.9

        return header_brands

    def _find_conclusion_mentions(
        self,
        text: str,
        brands: dict[str, EnhancedBrandExtraction],
    ) -> set[str]:
        """Find brands mentioned in conclusion."""
        conclusion_brands = set()

        for pattern in self._compiled_conclusions:
            for match in pattern.finditer(text):
                matched_text = match.group(1).lower() if match.lastindex else ""

                for normalized, brand in brands.items():
                    if normalized in matched_text or matched_text in brand.brand_name.lower():
                        conclusion_brands.add(normalized)

        return conclusion_brands

    def _calculate_priority_score(
        self,
        brand: EnhancedBrandExtraction,
        signals: list[PrioritySignal],
        signal_scores: dict[str, float],
    ) -> float:
        """Calculate overall priority score."""
        # Base score from position (first is better)
        position_score = 1.0 / brand.mention_rank

        # Signal bonus
        signal_bonus = sum(signal_scores.values()) / max(len(signal_scores), 1)

        # Mention count bonus (more mentions = more important)
        mention_bonus = min(0.3, brand.mention_count * 0.1)

        # Combine scores
        priority_score = (position_score * 0.4) + (signal_bonus * 0.4) + (mention_bonus * 0.2)

        return min(1.0, priority_score)


# ==================== Contextual Framing Analyzer ====================


class ContextualFramingAnalyzer:
    """
    Analyzes contextual framing and sentiment around brand mentions.

    Determines how brands are positioned in terms of:
    - Positive/negative/neutral framing
    - Comparative framing
    - Authority framing
    - Risk/caution framing
    """

    # Sentiment patterns
    POSITIVE_PATTERNS = [
        (r"\bexcellent\b", 1.0),
        (r"\boutstanding\b", 1.0),
        (r"\bamazing\b", 0.9),
        (r"\bgreat\b", 0.8),
        (r"\bgood\b", 0.6),
        (r"\bbest\b", 0.9),
        (r"\btop\b", 0.7),
        (r"\bleading\b", 0.8),
        (r"\brecommended\b", 0.9),
        (r"\bpopular\b", 0.7),
        (r"\breliable\b", 0.8),
        (r"\bpowerful\b", 0.7),
        (r"\beffective\b", 0.8),
        (r"\befficient\b", 0.7),
        (r"\binnovative\b", 0.7),
        (r"\brobust\b", 0.7),
        (r"\bseamless\b", 0.8),
        (r"\buser-friendly\b", 0.7),
    ]

    NEGATIVE_PATTERNS = [
        (r"\bpoor\b", -0.8),
        (r"\bbad\b", -0.8),
        (r"\bterrible\b", -1.0),
        (r"\bawful\b", -1.0),
        (r"\bdifficult\b", -0.5),
        (r"\bcomplicated\b", -0.5),
        (r"\bexpensive\b", -0.4),
        (r"\bslow\b", -0.5),
        (r"\blimited\b", -0.4),
        (r"\blacking\b", -0.5),
        (r"\bproblematic\b", -0.7),
        (r"\bfailed\b", -0.8),
        (r"\bfrustrating\b", -0.7),
        (r"\bdisappointing\b", -0.7),
        (r"\bweak\b", -0.6),
        (r"\bflawed\b", -0.7),
    ]

    COMPARATIVE_PATTERNS = [
        r"\bcompared\s+to\b",
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\bunlike\b",
        r"\bsimilar\s+to\b",
        r"\bbetter\s+than\b",
        r"\bworse\s+than\b",
        r"\balternative\s+to\b",
    ]

    AUTHORITATIVE_PATTERNS = [
        r"\bindustry\s+(?:leader|standard)\b",
        r"\bmarket\s+leader\b",
        r"\bwidely\s+(?:used|adopted)\b",
        r"\btrusted\s+by\b",
        r"\bestablished\b",
        r"\brenowned\b",
        r"\breputable\b",
        r"\bproven\b",
    ]

    CAUTIONARY_PATTERNS = [
        r"\bhowever\b",
        r"\bbut\b",
        r"\bcaveat\b",
        r"\bwarning\b",
        r"\bcareful\b",
        r"\bconsider\b",
        r"\bkeep\s+in\s+mind\b",
        r"\bnote\s+that\b",
        r"\bdownside\b",
        r"\blimitation\b",
    ]

    def __init__(self, context_window: int = 150):
        """
        Initialize contextual framing analyzer.

        Args:
            context_window: Characters of context to analyze.
        """
        self.context_window = context_window

        # Compile patterns
        self._positive = [(re.compile(p, re.IGNORECASE), w) for p, w in self.POSITIVE_PATTERNS]
        self._negative = [(re.compile(p, re.IGNORECASE), w) for p, w in self.NEGATIVE_PATTERNS]
        self._comparative = [re.compile(p, re.IGNORECASE) for p in self.COMPARATIVE_PATTERNS]
        self._authoritative = [re.compile(p, re.IGNORECASE) for p in self.AUTHORITATIVE_PATTERNS]
        self._cautionary = [re.compile(p, re.IGNORECASE) for p in self.CAUTIONARY_PATTERNS]

    def analyze(
        self,
        text: str,
        brands: list[EnhancedBrandExtraction],
    ) -> list[FramingAnalysis]:
        """
        Analyze contextual framing for each brand.

        Args:
            text: Full response text.
            brands: List of extracted brands.

        Returns:
            Framing analysis for each brand.
        """
        results = []

        for brand in brands:
            context = self._get_brand_context(text, brand)

            # Analyze sentiment
            sentiment_score, sentiment_words = self._analyze_sentiment(context)

            # Determine framing type
            framing_type, indicators = self._determine_framing_type(context, sentiment_score)

            analysis = FramingAnalysis(
                brand_name=brand.brand_name,
                framing_type=framing_type,
                framing_score=sentiment_score,
                context_snippet=context,
                framing_indicators=indicators,
                sentiment_words=sentiment_words,
            )

            results.append(analysis)

        return results

    def _get_brand_context(
        self,
        text: str,
        brand: EnhancedBrandExtraction,
    ) -> str:
        """Get context around brand mention."""
        pos = brand.position_in_response
        start = max(0, pos - self.context_window)
        end = min(len(text), pos + len(brand.brand_name) + self.context_window)
        return text[start:end]

    def _analyze_sentiment(self, context: str) -> tuple[float, list[str]]:
        """Analyze sentiment in context."""
        positive_score = 0
        negative_score = 0
        sentiment_words = []

        for pattern, weight in self._positive:
            matches = pattern.findall(context)
            if matches:
                positive_score += weight * len(matches)
                sentiment_words.extend(matches)

        for pattern, weight in self._negative:
            matches = pattern.findall(context)
            if matches:
                negative_score += abs(weight) * len(matches)
                sentiment_words.extend(matches)

        # Calculate normalized score (-1 to 1)
        total = positive_score + negative_score
        if total == 0:
            return 0.0, sentiment_words

        score = (positive_score - negative_score) / total
        return max(-1.0, min(1.0, score)), sentiment_words

    def _determine_framing_type(
        self,
        context: str,
        sentiment_score: float,
    ) -> tuple[FramingType, list[str]]:
        """Determine the framing type based on patterns."""
        indicators = []

        # Check for comparative framing
        for pattern in self._comparative:
            if pattern.search(context):
                indicators.append("comparative")
                return FramingType.COMPARATIVE, indicators

        # Check for authoritative framing
        for pattern in self._authoritative:
            if pattern.search(context):
                indicators.append("authoritative")
                return FramingType.AUTHORITATIVE, indicators

        # Check for cautionary framing
        cautionary_count = 0
        for pattern in self._cautionary:
            if pattern.search(context):
                cautionary_count += 1
                indicators.append("cautionary")

        if cautionary_count >= 2:
            return FramingType.CAUTIONARY, indicators

        # Base on sentiment
        if sentiment_score > 0.3:
            return FramingType.POSITIVE, indicators
        elif sentiment_score < -0.3:
            return FramingType.NEGATIVE, indicators
        else:
            return FramingType.NEUTRAL, indicators
