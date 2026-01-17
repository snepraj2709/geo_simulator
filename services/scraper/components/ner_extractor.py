"""
Named Entity Recognition (NER) Extractor component.

Uses spaCy for entity extraction with fallback to regex-based extraction.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Try to import spaCy, with graceful fallback
try:
    import spacy
    from spacy.language import Language

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not installed. Using regex-based fallback for NER.")


@dataclass
class NamedEntity:
    """A named entity extracted from text."""
    text: str
    label: str  # ORG, PERSON, PRODUCT, GPE, MONEY, DATE, etc.
    start: int
    end: int
    confidence: float = 1.0
    source: str = "spacy"


@dataclass
class ExtractedNamedEntities:
    """Collection of named entities from text."""
    organizations: list[NamedEntity] = field(default_factory=list)
    persons: list[NamedEntity] = field(default_factory=list)
    products: list[NamedEntity] = field(default_factory=list)
    locations: list[NamedEntity] = field(default_factory=list)
    money: list[NamedEntity] = field(default_factory=list)
    dates: list[NamedEntity] = field(default_factory=list)
    events: list[NamedEntity] = field(default_factory=list)
    misc: list[NamedEntity] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Convert to dictionary."""
        def entity_to_dict(e: NamedEntity) -> dict[str, Any]:
            return {
                "text": e.text,
                "label": e.label,
                "confidence": e.confidence,
                "source": e.source,
            }

        return {
            "organizations": [entity_to_dict(e) for e in self.organizations],
            "persons": [entity_to_dict(e) for e in self.persons],
            "products": [entity_to_dict(e) for e in self.products],
            "locations": [entity_to_dict(e) for e in self.locations],
            "money": [entity_to_dict(e) for e in self.money],
            "dates": [entity_to_dict(e) for e in self.dates],
            "events": [entity_to_dict(e) for e in self.events],
            "misc": [entity_to_dict(e) for e in self.misc],
        }

    def get_all_organizations(self) -> list[str]:
        """Get unique organization names."""
        return list(set(e.text for e in self.organizations))

    def get_all_products(self) -> list[str]:
        """Get unique product names."""
        return list(set(e.text for e in self.products))

    def get_all_locations(self) -> list[str]:
        """Get unique location names."""
        return list(set(e.text for e in self.locations))


class NERExtractor:
    """
    Named Entity Recognition extractor.

    Uses spaCy's NER capabilities when available, with regex fallback.
    Extracts organizations, persons, products, locations, money, dates, etc.
    """

    # spaCy model name
    SPACY_MODEL = "en_core_web_sm"

    # Mapping from spaCy labels to our categories
    LABEL_MAPPING = {
        "ORG": "organizations",
        "PERSON": "persons",
        "PRODUCT": "products",
        "GPE": "locations",  # Geopolitical entities
        "LOC": "locations",  # Locations
        "FAC": "locations",  # Facilities
        "MONEY": "money",
        "DATE": "dates",
        "TIME": "dates",
        "EVENT": "events",
        "WORK_OF_ART": "products",
        "LAW": "misc",
        "LANGUAGE": "misc",
        "NORP": "misc",  # Nationalities, religious, political groups
    }

    # Regex patterns for fallback extraction
    FALLBACK_PATTERNS = {
        "organizations": [
            # Company names with common suffixes
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Inc|LLC|Ltd|Corp|Company|Co|Group|Holdings|Partners|Solutions|Technologies|Software|Systems|Services)\.?))\b",
            # Known tech companies
            r"\b(Google|Microsoft|Amazon|Apple|Meta|Facebook|Netflix|Salesforce|Oracle|SAP|IBM|Cisco|Adobe|VMware|Slack|Zoom|Atlassian|HubSpot|Zendesk)\b",
        ],
        "persons": [
            # Common name patterns
            r"\b((?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
            r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)(?:,\s*(?:CEO|CTO|CFO|COO|Founder|Director|VP|President))\b",
        ],
        "products": [
            # Product patterns
            r"\b([A-Z][a-z]*(?:Pro|Plus|Enterprise|Premium|Cloud|Hub|AI|ML|API|SDK))\b",
            r"\b([A-Z][a-z]+\s+(?:Platform|Suite|Studio|App|Tool|Dashboard|Manager|Analyzer))\b",
        ],
        "locations": [
            # US States
            r"\b(Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming)\b",
            # Major cities
            r"\b(New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose|Austin|Jacksonville|Fort Worth|Columbus|Charlotte|San Francisco|Indianapolis|Seattle|Denver|Boston|Nashville|Baltimore|Oklahoma City|Louisville|Portland|Las Vegas|Milwaukee|Albuquerque|Tucson|Fresno|Sacramento|Mesa|Kansas City|Atlanta|Miami|Oakland|Minneapolis|Tulsa|Cleveland|Wichita|Arlington|New Orleans)\b",
            # Country names
            r"\b(United States|USA|UK|United Kingdom|Canada|Germany|France|Japan|China|India|Australia|Brazil|Mexico|Spain|Italy|Netherlands|Sweden|Switzerland|Singapore|South Korea)\b",
        ],
        "money": [
            r"\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|M|B|K))?",
            r"(?:USD|EUR|GBP|JPY)\s*[\d,]+(?:\.\d{2})?",
            r"[\d,]+(?:\.\d{2})?\s*(?:dollars?|euros?|pounds?)",
        ],
        "dates": [
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}\b",
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b(?:Q[1-4]|FY)\s*\d{2,4}\b",
            r"\b\d{4}\b",  # Years
        ],
    }

    def __init__(self, use_spacy: bool = True):
        """
        Initialize NER Extractor.

        Args:
            use_spacy: Whether to use spaCy if available.
        """
        self._nlp = None
        self._use_spacy = use_spacy and SPACY_AVAILABLE
        self._compiled_patterns = {}

        if self._use_spacy:
            self._load_spacy_model()
        else:
            self._compile_fallback_patterns()

    def _load_spacy_model(self) -> None:
        """Load spaCy model."""
        try:
            self._nlp = spacy.load(self.SPACY_MODEL)
            logger.info("Loaded spaCy model: %s", self.SPACY_MODEL)
        except OSError:
            logger.warning(
                "spaCy model '%s' not found. Attempting to download...",
                self.SPACY_MODEL
            )
            try:
                from spacy.cli import download
                download(self.SPACY_MODEL)
                self._nlp = spacy.load(self.SPACY_MODEL)
                logger.info("Downloaded and loaded spaCy model: %s", self.SPACY_MODEL)
            except Exception as e:
                logger.error("Failed to download spaCy model: %s", e)
                self._use_spacy = False
                self._compile_fallback_patterns()

    def _compile_fallback_patterns(self) -> None:
        """Compile regex patterns for fallback extraction."""
        for category, patterns in self.FALLBACK_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE if category in ("dates", "money") else 0)
                for p in patterns
            ]

    def extract(self, text: str, max_length: int = 100000) -> ExtractedNamedEntities:
        """
        Extract named entities from text.

        Args:
            text: Text to analyze.
            max_length: Maximum text length to process.

        Returns:
            ExtractedNamedEntities with all found entities.
        """
        if not text:
            return ExtractedNamedEntities()

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        if self._use_spacy and self._nlp:
            return self._extract_with_spacy(text)
        else:
            return self._extract_with_regex(text)

    def _extract_with_spacy(self, text: str) -> ExtractedNamedEntities:
        """Extract entities using spaCy."""
        entities = ExtractedNamedEntities()

        try:
            doc = self._nlp(text)

            for ent in doc.ents:
                entity = NamedEntity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0,
                    source="spacy",
                )

                # Map to category
                category = self.LABEL_MAPPING.get(ent.label_)
                if category:
                    getattr(entities, category).append(entity)

            # Deduplicate
            self._deduplicate_entities(entities)

        except Exception as e:
            logger.error("spaCy extraction failed: %s", e)
            # Fall back to regex
            return self._extract_with_regex(text)

        return entities

    def _extract_with_regex(self, text: str) -> ExtractedNamedEntities:
        """Extract entities using regex patterns."""
        entities = ExtractedNamedEntities()

        for category, patterns in self._compiled_patterns.items():
            entity_list = getattr(entities, category)

            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity = NamedEntity(
                        text=match.group(1) if match.lastindex else match.group(0),
                        label=category.upper(),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.7,
                        source="regex",
                    )
                    entity_list.append(entity)

        # Deduplicate
        self._deduplicate_entities(entities)

        return entities

    def _deduplicate_entities(self, entities: ExtractedNamedEntities) -> None:
        """Remove duplicate entities within each category."""
        for category in ["organizations", "persons", "products", "locations",
                         "money", "dates", "events", "misc"]:
            entity_list = getattr(entities, category)
            seen = set()
            unique = []

            for entity in entity_list:
                key = entity.text.lower().strip()
                if key not in seen and len(key) > 1:
                    seen.add(key)
                    unique.append(entity)

            setattr(entities, category, unique)

    def extract_organizations(self, text: str) -> list[str]:
        """Extract only organization names."""
        entities = self.extract(text)
        return entities.get_all_organizations()

    def extract_products(self, text: str) -> list[str]:
        """Extract only product names."""
        entities = self.extract(text)
        return entities.get_all_products()

    def extract_locations(self, text: str) -> list[str]:
        """Extract only location names."""
        entities = self.extract(text)
        return entities.get_all_locations()

    def extract_with_context(
        self,
        text: str,
        context_window: int = 50,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Extract entities with surrounding context.

        Args:
            text: Text to analyze.
            context_window: Characters of context to include.

        Returns:
            Dictionary mapping category to entities with context.
        """
        entities = self.extract(text)
        result = {}

        for category in ["organizations", "persons", "products", "locations"]:
            entity_list = getattr(entities, category)
            result[category] = []

            for entity in entity_list:
                start = max(0, entity.start - context_window)
                end = min(len(text), entity.end + context_window)
                context = text[start:end]

                result[category].append({
                    "text": entity.text,
                    "label": entity.label,
                    "context": context,
                    "confidence": entity.confidence,
                })

        return result


class CompetitorDetector:
    """
    Detects competitor mentions in web content.

    Uses NER combined with domain-specific heuristics.
    """

    # Common competitor indicator phrases
    COMPETITOR_INDICATORS = [
        "vs", "versus", "alternative to", "compared to", "competitor",
        "better than", "instead of", "switch from", "migrate from",
    ]

    def __init__(self, ner_extractor: NERExtractor | None = None):
        """
        Initialize Competitor Detector.

        Args:
            ner_extractor: NER extractor instance.
        """
        self.ner = ner_extractor or NERExtractor()

    def detect_competitors(
        self,
        text: str,
        own_brand: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Detect competitor mentions in text.

        Args:
            text: Text to analyze.
            own_brand: Own brand name to exclude.

        Returns:
            List of competitor mentions with context.
        """
        competitors = []
        text_lower = text.lower()

        # Extract organizations
        entities = self.ner.extract(text)
        orgs = entities.get_all_organizations()

        # Look for competitor indicators near organization mentions
        for org in orgs:
            if own_brand and org.lower() == own_brand.lower():
                continue

            org_lower = org.lower()
            # Find position of org in text
            pos = text_lower.find(org_lower)

            if pos >= 0:
                # Check for competitor indicators nearby
                context_start = max(0, pos - 100)
                context_end = min(len(text), pos + len(org) + 100)
                context = text[context_start:context_end].lower()

                is_competitor = False
                indicator_found = None

                for indicator in self.COMPETITOR_INDICATORS:
                    if indicator in context:
                        is_competitor = True
                        indicator_found = indicator
                        break

                if is_competitor:
                    competitors.append({
                        "name": org,
                        "indicator": indicator_found,
                        "context": text[context_start:context_end],
                        "confidence": 0.7,
                    })

        return competitors

    def extract_comparison_table(
        self,
        html: str,
    ) -> list[dict[str, Any]]:
        """
        Extract competitor comparison from tables.

        Args:
            html: HTML content.

        Returns:
            List of competitors from comparison tables.
        """
        competitors = []

        # Look for comparison table patterns
        table_pattern = re.compile(
            r'<table[^>]*class=["\'][^"\']*(?:comparison|feature|pricing)[^"\']*["\'][^>]*>.*?</table>',
            re.IGNORECASE | re.DOTALL
        )

        for match in table_pattern.finditer(html):
            table_html = match.group(0)

            # Extract headers (potential competitor names)
            header_pattern = re.compile(r'<th[^>]*>([^<]+)</th>', re.IGNORECASE)
            headers = header_pattern.findall(table_html)

            for header in headers:
                header_clean = header.strip()
                if header_clean and len(header_clean) > 2:
                    # Skip common non-competitor headers
                    if header_clean.lower() not in ("feature", "price", "free", "starter", "pro", "enterprise"):
                        competitors.append({
                            "name": header_clean,
                            "source": "comparison_table",
                            "confidence": 0.8,
                        })

        return competitors
