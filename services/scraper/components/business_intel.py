"""
Business Intelligence Extraction module.

Extracts structured business information from web content:
- Product/service offerings
- Company description
- Target audience signals
- Key value propositions
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ProductOffering:
    """Extracted product offering."""
    name: str
    description: str | None = None
    category: str | None = None
    features: list[str] = field(default_factory=list)
    pricing: str | None = None
    confidence: float = 0.5
    source: str = "text"


@dataclass
class ServiceOffering:
    """Extracted service offering."""
    name: str
    description: str | None = None
    category: str | None = None
    deliverables: list[str] = field(default_factory=list)
    pricing: str | None = None
    confidence: float = 0.5
    source: str = "text"


@dataclass
class TargetAudienceSignal:
    """Signal indicating target audience."""
    segment: str
    evidence: str
    confidence: float = 0.5
    source: str = "text"


@dataclass
class ValueProposition:
    """Extracted value proposition."""
    statement: str
    benefit_type: str  # cost, time, quality, risk, convenience
    target_pain_point: str | None = None
    confidence: float = 0.5


@dataclass
class CompanyProfile:
    """Extracted company profile."""
    name: str | None = None
    description: str | None = None
    tagline: str | None = None
    mission_statement: str | None = None
    founding_year: int | None = None
    company_size: str | None = None
    headquarters: str | None = None
    industry: str | None = None


@dataclass
class BusinessIntelligence:
    """Aggregated business intelligence from website."""
    company_profile: CompanyProfile = field(default_factory=CompanyProfile)
    products: list[ProductOffering] = field(default_factory=list)
    services: list[ServiceOffering] = field(default_factory=list)
    value_propositions: list[ValueProposition] = field(default_factory=list)
    target_audience: list[TargetAudienceSignal] = field(default_factory=list)
    competitors_mentioned: list[str] = field(default_factory=list)
    technologies_used: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    partnerships: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "company_profile": {
                "name": self.company_profile.name,
                "description": self.company_profile.description,
                "tagline": self.company_profile.tagline,
                "mission_statement": self.company_profile.mission_statement,
                "founding_year": self.company_profile.founding_year,
                "company_size": self.company_profile.company_size,
                "headquarters": self.company_profile.headquarters,
                "industry": self.company_profile.industry,
            },
            "products": [
                {
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "features": p.features,
                    "pricing": p.pricing,
                    "confidence": p.confidence,
                    "source": p.source,
                }
                for p in self.products
            ],
            "services": [
                {
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                    "deliverables": s.deliverables,
                    "pricing": s.pricing,
                    "confidence": s.confidence,
                    "source": s.source,
                }
                for s in self.services
            ],
            "value_propositions": [
                {
                    "statement": v.statement,
                    "benefit_type": v.benefit_type,
                    "target_pain_point": v.target_pain_point,
                    "confidence": v.confidence,
                }
                for v in self.value_propositions
            ],
            "target_audience": [
                {
                    "segment": t.segment,
                    "evidence": t.evidence,
                    "confidence": t.confidence,
                    "source": t.source,
                }
                for t in self.target_audience
            ],
            "competitors_mentioned": self.competitors_mentioned,
            "technologies_used": self.technologies_used,
            "certifications": self.certifications,
            "partnerships": self.partnerships,
        }


class BusinessIntelligenceExtractor:
    """
    Extracts structured business intelligence from web content.

    Focuses on:
    - Product/service offerings with details
    - Company description and profile
    - Target audience signals
    - Value propositions and differentiators
    """

    # Patterns for value proposition extraction
    VALUE_PROP_PATTERNS = [
        # Time savings
        (r"(?:save|reduce|cut)\s+(?:up\s+to\s+)?(\d+[%]?\s*(?:hours?|days?|weeks?|time))", "time"),
        (r"(\d+x?\s*faster)", "time"),
        (r"(streamline|automate|simplify)\s+(?:your\s+)?(\w+)", "time"),

        # Cost savings
        (r"(?:save|reduce|cut)\s+(?:up\s+to\s+)?(\$?[\d,]+[kKmM]?|\d+[%]?\s*(?:cost|expense|spending))", "cost"),
        (r"(free\s+(?:trial|tier|plan))", "cost"),
        (r"(no\s+(?:credit\s+card|setup\s+fee|hidden\s+cost))", "cost"),

        # Quality improvements
        (r"(\d+[%]?\s*(?:more\s+)?(?:accurate|reliable|effective))", "quality"),
        (r"(industry[- ]leading|best[- ]in[- ]class|enterprise[- ]grade)", "quality"),
        (r"(99\.?\d*[%]?\s*(?:uptime|availability|accuracy))", "quality"),

        # Risk reduction
        (r"(secure|compliant|certified|encrypted)", "risk"),
        (r"(SOC\s*2|HIPAA|GDPR|ISO\s*\d+)", "risk"),
        (r"(money[- ]back\s+guarantee|risk[- ]free)", "risk"),

        # Convenience
        (r"(no\s+code|low\s+code|drag[- ]and[- ]drop)", "convenience"),
        (r"(one[- ]click|instant|easy\s+(?:to\s+)?(?:use|setup|integrate))", "convenience"),
        (r"(works\s+with|integrates?\s+with)\s+(\w+)", "convenience"),
    ]

    # Target audience indicators
    AUDIENCE_PATTERNS = [
        (r"(?:for|designed\s+for|built\s+for|perfect\s+for)\s+([\w\s]+(?:teams?|companies?|businesses?|startups?|enterprises?))", "explicit"),
        (r"(?:small\s+)?(?:business(?:es)?|SMBs?|startups?|enterprises?|agencies?|freelancers?)", "company_size"),
        (r"(?:marketing|sales|engineering|hr|finance|operations?|product)\s+teams?", "department"),
        (r"(?:CEO|CTO|CMO|CFO|founder|developer|marketer|designer|manager|executive)s?", "role"),
        (r"(?:B2B|B2C|SaaS|ecommerce|e-commerce|retail|healthcare|fintech)", "industry"),
    ]

    # Company profile patterns
    COMPANY_PATTERNS = {
        "tagline": [
            r"<meta[^>]+(?:name|property)=[\"'](?:og:)?description[\"'][^>]+content=[\"']([^\"']+)[\"']",
            r"<h1[^>]*class=[\"'][^\"']*(?:tagline|slogan|hero)[^\"']*[\"'][^>]*>([^<]+)</h1>",
        ],
        "founding_year": [
            r"(?:founded|established|since|started)\s+(?:in\s+)?(\d{4})",
        ],
        "company_size": [
            r"(\d+[,\d]*\+?\s*(?:employees?|team\s+members?|people))",
            r"(team\s+of\s+\d+)",
        ],
        "headquarters": [
            r"(?:headquartered|based|located)\s+in\s+([A-Z][a-z]+(?:\s*,\s*[A-Z]{2})?)",
        ],
    }

    # Product section indicators
    PRODUCT_SECTION_PATTERNS = [
        r"<(?:section|div)[^>]*(?:class|id)=[\"'][^\"']*(?:product|solution|platform|feature)[^\"']*[\"']",
        r"<h[1-3][^>]*>(?:Our\s+)?(?:Products?|Solutions?|Platform|Features?)</h[1-3]>",
    ]

    # Service section indicators
    SERVICE_SECTION_PATTERNS = [
        r"<(?:section|div)[^>]*(?:class|id)=[\"'][^\"']*(?:service|offering|solution)[^\"']*[\"']",
        r"<h[1-3][^>]*>(?:Our\s+)?(?:Services?|Offerings?|What\s+We\s+(?:Do|Offer))</h[1-3]>",
    ]

    def __init__(self):
        """Initialize Business Intelligence Extractor."""
        self._compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        for category, patterns in [
            ("value_prop", self.VALUE_PROP_PATTERNS),
            ("audience", self.AUDIENCE_PATTERNS),
        ]:
            self._compiled_patterns[category] = [
                (re.compile(p[0], re.IGNORECASE), p[1])
                for p in patterns
            ]

    def extract(
        self,
        content_text: str,
        html: str,
        headings: list[dict[str, str]],
        structured_data: list[dict[str, Any]],
        meta_description: str | None,
        title: str | None,
        domain: str,
    ) -> BusinessIntelligence:
        """
        Extract business intelligence from page content.

        Args:
            content_text: Extracted text content.
            html: Raw HTML content.
            headings: Page headings.
            structured_data: JSON-LD structured data.
            meta_description: Page meta description.
            title: Page title.
            domain: Website domain.

        Returns:
            BusinessIntelligence with extracted data.
        """
        intel = BusinessIntelligence()

        # Extract company profile
        intel.company_profile = self._extract_company_profile(
            content_text, html, structured_data, meta_description, title, domain
        )

        # Extract products and services
        intel.products = self._extract_products(content_text, html, headings, structured_data)
        intel.services = self._extract_services(content_text, html, headings, structured_data)

        # Extract value propositions
        intel.value_propositions = self._extract_value_propositions(content_text, headings)

        # Extract target audience signals
        intel.target_audience = self._extract_target_audience(content_text, headings)

        # Extract additional info
        intel.technologies_used = self._extract_technologies(content_text)
        intel.certifications = self._extract_certifications(content_text)
        intel.partnerships = self._extract_partnerships(content_text, structured_data)

        return intel

    def _extract_company_profile(
        self,
        content_text: str,
        html: str,
        structured_data: list[dict[str, Any]],
        meta_description: str | None,
        title: str | None,
        domain: str,
    ) -> CompanyProfile:
        """Extract company profile information."""
        profile = CompanyProfile()

        # Extract from structured data (highest priority)
        for data in structured_data:
            schema_type = data.get("@type", "")
            if schema_type in ("Organization", "Corporation", "LocalBusiness"):
                profile.name = data.get("name") or profile.name
                profile.description = data.get("description") or profile.description

                address = data.get("address", {})
                if isinstance(address, dict):
                    locality = address.get("addressLocality", "")
                    region = address.get("addressRegion", "")
                    if locality or region:
                        profile.headquarters = f"{locality}, {region}".strip(", ")

                if data.get("foundingDate"):
                    try:
                        profile.founding_year = int(data["foundingDate"][:4])
                    except (ValueError, TypeError):
                        pass

        # Extract company name from title if not found
        if not profile.name and title:
            # Remove common suffixes
            name = title
            for suffix in [" - Home", " | Home", " - Official", " | Official", " - ", " | "]:
                if suffix in name:
                    name = name.split(suffix)[0].strip()
                    break
            if len(name) < 50:
                profile.name = name

        # Fall back to domain name
        if not profile.name:
            domain_parts = domain.replace("www.", "").split(".")
            if domain_parts:
                profile.name = domain_parts[0].title()

        # Use meta description as company description if suitable
        if not profile.description and meta_description:
            if len(meta_description) > 50:
                profile.description = meta_description

        # Extract tagline from first prominent heading or hero section
        if not profile.tagline:
            tagline_match = re.search(
                r'<(?:h1|p)[^>]*class=["\'][^"\']*(?:tagline|slogan|subtitle|hero)[^"\']*["\'][^>]*>([^<]+)',
                html, re.IGNORECASE
            )
            if tagline_match:
                profile.tagline = tagline_match.group(1).strip()

        # Extract founding year
        if not profile.founding_year:
            year_match = re.search(
                r"(?:founded|established|since|started)\s+(?:in\s+)?(\d{4})",
                content_text, re.IGNORECASE
            )
            if year_match:
                try:
                    year = int(year_match.group(1))
                    if 1900 < year <= 2025:
                        profile.founding_year = year
                except ValueError:
                    pass

        # Extract company size
        if not profile.company_size:
            size_match = re.search(
                r"(\d+[,\d]*\+?)\s*(?:employees?|team\s+members?|people)",
                content_text, re.IGNORECASE
            )
            if size_match:
                profile.company_size = size_match.group(0)

        # Detect industry from content
        if not profile.industry:
            profile.industry = self._detect_industry(content_text)

        return profile

    def _extract_products(
        self,
        content_text: str,
        html: str,
        headings: list[dict[str, str]],
        structured_data: list[dict[str, Any]],
    ) -> list[ProductOffering]:
        """Extract product offerings."""
        products = []
        seen_names = set()

        # Extract from structured data first
        for data in structured_data:
            if data.get("@type") in ("Product", "SoftwareApplication"):
                name = data.get("name", "").strip()
                if name and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    products.append(ProductOffering(
                        name=name,
                        description=data.get("description"),
                        category=data.get("category") or data.get("applicationCategory"),
                        pricing=self._extract_price_from_structured(data),
                        confidence=0.9,
                        source="structured_data",
                    ))

        # Extract from headings in product sections
        product_headings = [
            h for h in headings
            if any(kw in h["text"].lower() for kw in ["product", "solution", "platform", "feature"])
            and h["level"] in ("h1", "h2", "h3")
        ]

        for heading in product_headings:
            name = heading["text"].strip()
            if name and name.lower() not in seen_names and len(name) < 100:
                # Skip generic headings
                if name.lower() not in ("our products", "products", "our solutions", "solutions"):
                    seen_names.add(name.lower())
                    products.append(ProductOffering(
                        name=name,
                        confidence=0.6,
                        source="heading",
                    ))

        # Look for product cards/items in HTML
        product_card_pattern = re.compile(
            r'<(?:div|article|li)[^>]*class=["\'][^"\']*(?:product|card|item)[^"\']*["\'][^>]*>.*?'
            r'<(?:h[2-4]|strong|b)[^>]*>([^<]+)</(?:h[2-4]|strong|b)>',
            re.IGNORECASE | re.DOTALL
        )

        for match in product_card_pattern.finditer(html):
            name = match.group(1).strip()
            if name and name.lower() not in seen_names and 3 < len(name) < 80:
                seen_names.add(name.lower())
                products.append(ProductOffering(
                    name=name,
                    confidence=0.5,
                    source="html_pattern",
                ))

        return products[:20]  # Limit to top 20

    def _extract_services(
        self,
        content_text: str,
        html: str,
        headings: list[dict[str, str]],
        structured_data: list[dict[str, Any]],
    ) -> list[ServiceOffering]:
        """Extract service offerings."""
        services = []
        seen_names = set()

        # Extract from structured data first
        for data in structured_data:
            if data.get("@type") == "Service":
                name = data.get("name", "").strip()
                if name and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    services.append(ServiceOffering(
                        name=name,
                        description=data.get("description"),
                        confidence=0.9,
                        source="structured_data",
                    ))

        # Extract from headings in service sections
        service_keywords = ["service", "consulting", "support", "training", "implementation"]
        service_headings = [
            h for h in headings
            if any(kw in h["text"].lower() for kw in service_keywords)
            and h["level"] in ("h1", "h2", "h3")
        ]

        for heading in service_headings:
            name = heading["text"].strip()
            if name and name.lower() not in seen_names and len(name) < 100:
                if name.lower() not in ("our services", "services"):
                    seen_names.add(name.lower())
                    services.append(ServiceOffering(
                        name=name,
                        confidence=0.6,
                        source="heading",
                    ))

        # Look for service patterns in text
        service_pattern = re.compile(
            r"(?:we\s+(?:offer|provide)|our\s+services?\s+include)\s*:?\s*([^.]+)",
            re.IGNORECASE
        )

        for match in service_pattern.finditer(content_text):
            text = match.group(1).strip()
            # Split by common delimiters
            for item in re.split(r"[,;•\n]", text):
                name = item.strip()
                if name and name.lower() not in seen_names and 5 < len(name) < 80:
                    seen_names.add(name.lower())
                    services.append(ServiceOffering(
                        name=name,
                        confidence=0.5,
                        source="text_pattern",
                    ))

        return services[:20]

    def _extract_value_propositions(
        self,
        content_text: str,
        headings: list[dict[str, str]],
    ) -> list[ValueProposition]:
        """Extract value propositions."""
        value_props = []
        seen = set()

        # Extract from patterns
        for pattern, benefit_type in self._compiled_patterns["value_prop"]:
            for match in pattern.finditer(content_text):
                statement = match.group(0).strip()
                if statement and statement.lower() not in seen:
                    seen.add(statement.lower())
                    value_props.append(ValueProposition(
                        statement=statement,
                        benefit_type=benefit_type,
                        confidence=0.7,
                    ))

        # Extract from hero/headline sections
        hero_keywords = ["transform", "revolutionize", "simplify", "accelerate", "maximize"]
        for heading in headings:
            if heading["level"] in ("h1", "h2"):
                text = heading["text"].lower()
                for keyword in hero_keywords:
                    if keyword in text:
                        value_props.append(ValueProposition(
                            statement=heading["text"],
                            benefit_type="quality",
                            confidence=0.6,
                        ))
                        break

        return value_props[:15]

    def _extract_target_audience(
        self,
        content_text: str,
        headings: list[dict[str, str]],
    ) -> list[TargetAudienceSignal]:
        """Extract target audience signals."""
        signals = []
        seen = set()

        # Extract from patterns
        for pattern, signal_type in self._compiled_patterns["audience"]:
            for match in pattern.finditer(content_text):
                segment = match.group(0).strip()
                if segment and segment.lower() not in seen:
                    seen.add(segment.lower())

                    # Get context around the match
                    start = max(0, match.start() - 50)
                    end = min(len(content_text), match.end() + 50)
                    context = content_text[start:end]

                    signals.append(TargetAudienceSignal(
                        segment=segment,
                        evidence=context,
                        confidence=0.6 if signal_type == "explicit" else 0.5,
                        source=signal_type,
                    ))

        # Look for "for" statements in headings
        for heading in headings:
            if " for " in heading["text"].lower():
                text = heading["text"]
                signals.append(TargetAudienceSignal(
                    segment=text,
                    evidence=text,
                    confidence=0.7,
                    source="heading",
                ))

        return signals[:15]

    def _extract_technologies(self, content_text: str) -> list[str]:
        """Extract technology mentions."""
        technologies = []
        tech_keywords = [
            "api", "rest", "graphql", "webhook", "sdk", "oauth", "jwt",
            "saas", "cloud", "aws", "azure", "gcp", "docker", "kubernetes",
            "react", "vue", "angular", "next.js", "node", "python", "java",
            "ai", "machine learning", "nlp", "deep learning",
            "blockchain", "iot", "mobile", "native app",
            "postgresql", "mongodb", "redis", "elasticsearch",
        ]

        text_lower = content_text.lower()
        for tech in tech_keywords:
            pattern = r"\b" + re.escape(tech) + r"\b"
            if re.search(pattern, text_lower, re.IGNORECASE):
                technologies.append(tech.upper() if len(tech) <= 4 else tech.title())

        return list(set(technologies))

    def _extract_certifications(self, content_text: str) -> list[str]:
        """Extract certifications and compliance mentions."""
        certifications = []
        cert_patterns = [
            r"SOC\s*2(?:\s+Type\s*[12I]+)?",
            r"HIPAA(?:\s+compliant)?",
            r"GDPR(?:\s+compliant)?",
            r"ISO\s*\d{4,5}",
            r"PCI[- ]DSS",
            r"FedRAMP",
            r"CCPA",
            r"SOX\s+compliant",
        ]

        for pattern in cert_patterns:
            matches = re.findall(pattern, content_text, re.IGNORECASE)
            certifications.extend(matches)

        return list(set(certifications))

    def _extract_partnerships(
        self,
        content_text: str,
        structured_data: list[dict[str, Any]],
    ) -> list[str]:
        """Extract partnership/integration mentions."""
        partnerships = []

        # Check structured data for partners
        for data in structured_data:
            if data.get("@type") == "Organization":
                sponsor = data.get("sponsor")
                if sponsor:
                    if isinstance(sponsor, list):
                        partnerships.extend([s.get("name", "") for s in sponsor if s.get("name")])
                    elif isinstance(sponsor, dict):
                        if sponsor.get("name"):
                            partnerships.append(sponsor["name"])

        # Extract from text patterns
        partner_pattern = re.compile(
            r"(?:partner(?:s|ed|ship)?|integrat(?:es?|ion)|works?\s+with)\s+(?:with\s+)?"
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
            re.MULTILINE
        )

        for match in partner_pattern.finditer(content_text):
            partner = match.group(1).strip()
            if partner and 2 < len(partner) < 50:
                partnerships.append(partner)

        return list(set(partnerships))[:15]

    def _extract_price_from_structured(self, data: dict[str, Any]) -> str | None:
        """Extract price from structured data."""
        offers = data.get("offers")
        if not offers:
            return None

        if isinstance(offers, list):
            offers = offers[0] if offers else None

        if isinstance(offers, dict):
            price = offers.get("price")
            currency = offers.get("priceCurrency", "USD")
            if price:
                return f"{currency} {price}"

        return None

    def _detect_industry(self, content_text: str) -> str | None:
        """Detect primary industry from content."""
        industry_keywords = {
            "healthcare": ["healthcare", "medical", "health", "hospital", "patient", "clinical", "pharma"],
            "finance": ["finance", "financial", "banking", "fintech", "payment", "investment", "trading"],
            "ecommerce": ["ecommerce", "e-commerce", "retail", "shopping", "store", "commerce", "marketplace"],
            "education": ["education", "learning", "edtech", "school", "training", "course", "university"],
            "technology": ["technology", "tech", "software", "saas", "digital", "it ", "developer"],
            "marketing": ["marketing", "advertising", "martech", "seo", "social media", "campaign", "brand"],
            "real_estate": ["real estate", "property", "housing", "rental", "realty", "mortgage"],
            "logistics": ["logistics", "shipping", "supply chain", "delivery", "freight", "warehouse"],
            "manufacturing": ["manufacturing", "factory", "production", "industrial", "assembly"],
            "hospitality": ["hotel", "restaurant", "hospitality", "tourism", "travel", "booking"],
        }

        text_lower = content_text.lower()
        industry_scores = {}

        for industry, keywords in industry_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                industry_scores[industry] = score

        if industry_scores:
            return max(industry_scores, key=industry_scores.get)

        return None
