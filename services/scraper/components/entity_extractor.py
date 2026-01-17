"""
Entity Extractor component.

Extracts named entities, products, services, and other business-relevant
information from parsed content.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntities:
    """Extracted entities from page content."""
    products: list[dict[str, Any]] = field(default_factory=list)
    services: list[dict[str, Any]] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    pricing_mentions: list[dict[str, Any]] = field(default_factory=list)
    contact_info: dict[str, Any] = field(default_factory=dict)
    social_links: dict[str, str] = field(default_factory=dict)
    technologies: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)


class EntityExtractor:
    """
    Extracts business entities from parsed web content.

    Features:
    - Product/service detection
    - Brand mention extraction
    - Feature/benefit identification
    - Contact information extraction
    - Technology stack detection
    """

    # Common product/service indicator words
    PRODUCT_INDICATORS = [
        "product", "solution", "platform", "software", "tool",
        "app", "application", "system", "suite", "service",
    ]

    # Feature indicator patterns
    FEATURE_PATTERNS = [
        r"(?:feature|capability|function)(?:s)?:?\s*([^.]+)",
        r"(?:include|includes|including|with)\s+([^.]+)",
        r"•\s*([^•\n]+)",  # Bullet points
        r"✓\s*([^✓\n]+)",  # Checkmarks
    ]

    # Pricing patterns
    PRICING_PATTERNS = [
        r"\$[\d,]+(?:\.\d{2})?(?:\s*/?(?:mo|month|yr|year|user))?",
        r"(?:free|starter|basic|pro|premium|enterprise)\s*(?:plan|tier)?",
        r"(?:pricing|plans?)\s*(?:start(?:ing)?s?\s*(?:at|from))?\s*\$?[\d,]+",
    ]

    # Email pattern
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    # Phone pattern (US format primarily)
    PHONE_PATTERN = r"(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}"

    # Social media domains
    SOCIAL_DOMAINS = {
        "twitter.com": "twitter",
        "x.com": "twitter",
        "linkedin.com": "linkedin",
        "facebook.com": "facebook",
        "instagram.com": "instagram",
        "youtube.com": "youtube",
        "github.com": "github",
    }

    # Technology indicators
    TECH_KEYWORDS = [
        "api", "rest", "graphql", "webhook", "sdk", "oauth",
        "saas", "cloud", "aws", "azure", "gcp", "docker", "kubernetes",
        "react", "vue", "angular", "node", "python", "java",
        "ai", "ml", "machine learning", "artificial intelligence",
        "blockchain", "iot", "mobile", "native",
    ]

    # Industry keywords
    INDUSTRY_KEYWORDS = {
        "healthcare": ["healthcare", "medical", "health", "hospital", "patient", "clinical"],
        "finance": ["finance", "financial", "banking", "fintech", "payment", "investment"],
        "ecommerce": ["ecommerce", "e-commerce", "retail", "shopping", "store", "commerce"],
        "education": ["education", "learning", "edtech", "school", "training", "course"],
        "technology": ["technology", "tech", "software", "saas", "digital", "it"],
        "marketing": ["marketing", "advertising", "martech", "seo", "social media", "campaign"],
        "real_estate": ["real estate", "property", "housing", "rental", "realty"],
        "logistics": ["logistics", "shipping", "supply chain", "delivery", "freight"],
    }

    def __init__(self):
        """Initialize Entity Extractor."""
        pass

    def extract(
        self,
        content_text: str,
        headings: list[dict[str, str]],
        structured_data: list[dict[str, Any]],
        links: list[str],
        page_type: str,
    ) -> ExtractedEntities:
        """
        Extract entities from parsed content.

        Args:
            content_text: Main text content.
            headings: Page headings.
            structured_data: JSON-LD structured data.
            links: Page links.
            page_type: Type of page.

        Returns:
            ExtractedEntities with all found entities.
        """
        entities = ExtractedEntities()

        # Extract from structured data first (most reliable)
        self._extract_from_structured_data(structured_data, entities)

        # Extract from text content
        self._extract_products_services(content_text, headings, entities)
        self._extract_features_benefits(content_text, entities)
        self._extract_pricing(content_text, entities)
        self._extract_contact_info(content_text, entities)
        self._extract_technologies(content_text, entities)
        self._extract_industries(content_text, entities)

        # Extract from links
        self._extract_social_links(links, entities)

        return entities

    def _extract_from_structured_data(
        self,
        structured_data: list[dict[str, Any]],
        entities: ExtractedEntities,
    ) -> None:
        """Extract entities from JSON-LD structured data."""
        for data in structured_data:
            schema_type = data.get("@type", "")

            if schema_type == "Product":
                entities.products.append({
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "source": "structured_data",
                })

            elif schema_type == "Service":
                entities.services.append({
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "source": "structured_data",
                })

            elif schema_type == "Organization":
                # Extract brand info
                name = data.get("name")
                if name:
                    entities.brands.append(name)

                # Extract contact info
                if data.get("email"):
                    entities.contact_info["email"] = data["email"]
                if data.get("telephone"):
                    entities.contact_info["phone"] = data["telephone"]
                if data.get("address"):
                    entities.contact_info["address"] = data["address"]

            elif schema_type == "SoftwareApplication":
                entities.products.append({
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                    "category": data.get("applicationCategory", ""),
                    "source": "structured_data",
                })

    def _extract_products_services(
        self,
        content_text: str,
        headings: list[dict[str, str]],
        entities: ExtractedEntities,
    ) -> None:
        """Extract product and service mentions from text."""
        text_lower = content_text.lower()

        # Check headings for product/service names
        for heading in headings:
            heading_text = heading["text"].lower()

            for indicator in self.PRODUCT_INDICATORS:
                if indicator in heading_text:
                    # This heading likely describes a product/service
                    entities.products.append({
                        "name": heading["text"],
                        "source": "heading",
                    })
                    break

        # Look for "our products" or "our services" sections
        product_section_pattern = r"our\s+(?:products?|solutions?)\s*[:\n]([^.]+)"
        service_section_pattern = r"our\s+services?\s*[:\n]([^.]+)"

        for match in re.finditer(product_section_pattern, text_lower, re.IGNORECASE):
            entities.products.append({
                "name": match.group(1).strip()[:100],
                "source": "text_pattern",
            })

        for match in re.finditer(service_section_pattern, text_lower, re.IGNORECASE):
            entities.services.append({
                "name": match.group(1).strip()[:100],
                "source": "text_pattern",
            })

    def _extract_features_benefits(
        self,
        content_text: str,
        entities: ExtractedEntities,
    ) -> None:
        """Extract features and benefits."""
        for pattern in self.FEATURE_PATTERNS:
            for match in re.finditer(pattern, content_text, re.IGNORECASE):
                feature = match.group(1).strip()
                if 5 < len(feature) < 200:  # Reasonable length
                    # Classify as feature or benefit
                    if any(word in feature.lower() for word in ["save", "improve", "increase", "reduce", "boost"]):
                        entities.benefits.append(feature)
                    else:
                        entities.features.append(feature)

        # Deduplicate
        entities.features = list(dict.fromkeys(entities.features))[:20]
        entities.benefits = list(dict.fromkeys(entities.benefits))[:20]

    def _extract_pricing(
        self,
        content_text: str,
        entities: ExtractedEntities,
    ) -> None:
        """Extract pricing information."""
        for pattern in self.PRICING_PATTERNS:
            for match in re.finditer(pattern, content_text, re.IGNORECASE):
                price_text = match.group(0).strip()
                entities.pricing_mentions.append({
                    "text": price_text,
                    "context": content_text[max(0, match.start()-50):match.end()+50],
                })

        # Deduplicate based on text
        seen = set()
        unique_pricing = []
        for pm in entities.pricing_mentions:
            if pm["text"] not in seen:
                seen.add(pm["text"])
                unique_pricing.append(pm)
        entities.pricing_mentions = unique_pricing[:10]

    def _extract_contact_info(
        self,
        content_text: str,
        entities: ExtractedEntities,
    ) -> None:
        """Extract contact information."""
        # Extract emails
        emails = re.findall(self.EMAIL_PATTERN, content_text)
        if emails:
            # Filter out common non-contact emails
            filtered = [
                e for e in emails
                if not any(skip in e.lower() for skip in ["noreply", "no-reply", "unsubscribe"])
            ]
            if filtered:
                entities.contact_info["emails"] = list(set(filtered))[:5]

        # Extract phone numbers
        phones = re.findall(self.PHONE_PATTERN, content_text)
        if phones:
            entities.contact_info["phones"] = list(set(phones))[:3]

    def _extract_social_links(
        self,
        links: list[str],
        entities: ExtractedEntities,
    ) -> None:
        """Extract social media links."""
        for link in links:
            link_lower = link.lower()
            for domain, platform in self.SOCIAL_DOMAINS.items():
                if domain in link_lower:
                    entities.social_links[platform] = link
                    break

    def _extract_technologies(
        self,
        content_text: str,
        entities: ExtractedEntities,
    ) -> None:
        """Extract technology mentions."""
        text_lower = content_text.lower()

        for tech in self.TECH_KEYWORDS:
            # Look for whole word matches
            pattern = r"\b" + re.escape(tech) + r"\b"
            if re.search(pattern, text_lower, re.IGNORECASE):
                entities.technologies.append(tech.upper() if len(tech) <= 4 else tech.title())

        entities.technologies = list(set(entities.technologies))

    def _extract_industries(
        self,
        content_text: str,
        entities: ExtractedEntities,
    ) -> None:
        """Extract industry mentions."""
        text_lower = content_text.lower()

        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities.industries.append(industry)
                    break

        entities.industries = list(set(entities.industries))

    def extract_brand_name(
        self,
        title: str | None,
        structured_data: list[dict[str, Any]],
        domain: str,
    ) -> str | None:
        """
        Extract the primary brand name for a website.

        Args:
            title: Page title.
            structured_data: Structured data.
            domain: Website domain.

        Returns:
            Brand name or None.
        """
        # Try structured data first
        for data in structured_data:
            if data.get("@type") in ("Organization", "Corporation", "LocalBusiness"):
                if data.get("name"):
                    return data["name"]

        # Try extracting from title
        if title:
            # Remove common suffixes
            for suffix in [" - Home", " | Home", " - Official", " | Official"]:
                if title.endswith(suffix):
                    return title[:-len(suffix)].strip()

            # If title has a separator, take the last part (often brand name)
            for sep in [" | ", " - ", " :: ", " — "]:
                if sep in title:
                    parts = title.split(sep)
                    # Brand is usually shorter part
                    shortest = min(parts, key=len).strip()
                    if 2 < len(shortest) < 50:
                        return shortest

            # Return title if short enough
            if len(title) < 50:
                return title

        # Fall back to domain name
        domain_parts = domain.split(".")
        if domain_parts:
            brand = domain_parts[0]
            if brand.lower() not in ("www", "app", "api"):
                return brand.title()

        return None
