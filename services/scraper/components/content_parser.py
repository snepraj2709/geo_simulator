"""
Content Parser component.

Parses HTML content to extract text, metadata, and structured data.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment, NavigableString

logger = logging.getLogger(__name__)


@dataclass
class ParsedContent:
    """Parsed content from a web page."""
    url: str
    title: str | None = None
    meta_description: str | None = None
    content_text: str = ""
    word_count: int = 0
    headings: list[dict[str, str]] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    structured_data: list[dict[str, Any]] = field(default_factory=list)
    page_type: str = "unknown"
    language: str | None = None
    canonical_url: str | None = None


class ContentParser:
    """
    Parses HTML content to extract meaningful data.

    Features:
    - Text extraction with noise removal
    - Metadata extraction
    - Link extraction
    - Structured data (JSON-LD) parsing
    - Page type classification
    """

    # Tags to remove entirely
    REMOVE_TAGS = [
        "script", "style", "noscript", "iframe", "svg",
        "canvas", "video", "audio", "map", "object", "embed",
    ]

    # Tags to skip when extracting text
    SKIP_TEXT_TAGS = [
        "nav", "header", "footer", "aside", "form",
        "button", "input", "select", "textarea",
    ]

    def __init__(self, base_url: str):
        """
        Initialize Content Parser.

        Args:
            base_url: Base URL for resolving relative links.
        """
        self.base_url = base_url
        self._domain = urlparse(base_url).netloc

    def parse(self, html: str, url: str) -> ParsedContent:
        """
        Parse HTML content.

        Args:
            html: Raw HTML content.
            url: URL of the page.

        Returns:
            ParsedContent with extracted data.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted tags
        for tag in soup.find_all(self.REMOVE_TAGS):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Extract components
        content = ParsedContent(url=url)
        content.title = self._extract_title(soup)
        content.meta_description = self._extract_meta_description(soup)
        content.content_text = self._extract_text(soup)
        content.word_count = self._count_words(content.content_text)
        content.headings = self._extract_headings(soup)
        content.links = self._extract_links(soup, url)
        content.images = self._extract_images(soup, url)
        content.structured_data = self._extract_structured_data(soup)
        content.page_type = self._classify_page_type(url, soup, content)
        content.language = self._extract_language(soup)
        content.canonical_url = self._extract_canonical(soup, url)

        return content

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        """Extract page title."""
        # Try <title> tag first
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        # Try og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return None

    def _extract_meta_description(self, soup: BeautifulSoup) -> str | None:
        """Extract meta description."""
        # Standard meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()

        return None

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract main text content."""
        # Try to find main content area
        main_content = (
            soup.find("main") or
            soup.find("article") or
            soup.find("div", class_=re.compile(r"content|main|body", re.I)) or
            soup.find("div", id=re.compile(r"content|main|body", re.I)) or
            soup.body
        )

        if not main_content:
            return ""

        # Extract text, skipping certain tags
        texts = []
        for element in main_content.descendants:
            if isinstance(element, NavigableString):
                parent = element.parent
                if parent and parent.name not in self.SKIP_TEXT_TAGS:
                    text = str(element).strip()
                    if text:
                        texts.append(text)

        # Join and clean
        full_text = " ".join(texts)
        full_text = re.sub(r"\s+", " ", full_text)
        full_text = full_text.strip()

        return full_text

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        return len(text.split())

    def _extract_headings(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Extract all headings."""
        headings = []
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                if text:
                    headings.append({
                        "level": f"h{level}",
                        "text": text[:500],  # Limit length
                    })
        return headings

    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> list[str]:
        """Extract all links, resolving relative URLs."""
        links = []
        seen = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            # Skip anchors, javascript, mailto, tel
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(current_url, href)

            # Normalize
            parsed = urlparse(absolute_url)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            normalized = normalized.rstrip("/")

            if normalized not in seen:
                seen.add(normalized)
                links.append(normalized)

        return links

    def _extract_images(self, soup: BeautifulSoup, current_url: str) -> list[dict[str, str]]:
        """Extract images with alt text."""
        images = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue

            # Resolve relative URLs
            absolute_src = urljoin(current_url, src)

            images.append({
                "src": absolute_src,
                "alt": img.get("alt", ""),
                "title": img.get("title", ""),
            })

        return images[:50]  # Limit to 50 images

    def _extract_structured_data(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract JSON-LD structured data."""
        structured = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, list):
                    structured.extend(data)
                else:
                    structured.append(data)
            except (json.JSONDecodeError, TypeError):
                continue

        return structured

    def _extract_language(self, soup: BeautifulSoup) -> str | None:
        """Extract page language."""
        html_tag = soup.find("html")
        if html_tag:
            return html_tag.get("lang")
        return None

    def _extract_canonical(self, soup: BeautifulSoup, current_url: str) -> str | None:
        """Extract canonical URL."""
        link = soup.find("link", rel="canonical")
        if link and link.get("href"):
            return urljoin(current_url, link["href"])
        return None

    def _classify_page_type(
        self,
        url: str,
        soup: BeautifulSoup,
        content: ParsedContent,
    ) -> str:
        """
        Classify the type of page.

        Returns one of: homepage, product, service, blog, about, contact, pricing, other
        """
        path = urlparse(url).path.lower()

        # URL-based classification
        if path in ("", "/", "/index", "/index.html", "/home"):
            return "homepage"

        path_mappings = {
            "/product": "product",
            "/products": "product",
            "/service": "service",
            "/services": "service",
            "/solution": "service",
            "/solutions": "service",
            "/blog": "blog",
            "/news": "blog",
            "/article": "blog",
            "/about": "about",
            "/about-us": "about",
            "/team": "about",
            "/contact": "contact",
            "/contact-us": "contact",
            "/pricing": "pricing",
            "/plans": "pricing",
            "/features": "product",
            "/platform": "product",
        }

        for pattern, page_type in path_mappings.items():
            if path.startswith(pattern) or pattern in path:
                return page_type

        # Check structured data
        for data in content.structured_data:
            schema_type = data.get("@type", "").lower()
            if "product" in schema_type:
                return "product"
            if "blogposting" in schema_type or "article" in schema_type:
                return "blog"
            if "organization" in schema_type or "aboutpage" in schema_type:
                return "about"
            if "contactpage" in schema_type:
                return "contact"

        return "other"

    def get_internal_links(self, links: list[str]) -> list[str]:
        """Filter links to only internal ones."""
        internal = []
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc == self._domain or parsed.netloc.endswith(f".{self._domain}"):
                internal.append(link)
        return internal

    def get_external_links(self, links: list[str]) -> list[str]:
        """Filter links to only external ones."""
        external = []
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc != self._domain and not parsed.netloc.endswith(f".{self._domain}"):
                external.append(link)
        return external
