"""
Scraper components.

Based on ARCHITECTURE.md Website Scraper Service diagram:
- URL Queue Manager
- Content Parser
- Rate Limiter
- Entity Extractor
- Storage Handler
- Business Intelligence Extractor
- NER Extractor
"""

from services.scraper.components.url_queue import URLQueueManager
from services.scraper.components.content_parser import ContentParser
from services.scraper.components.rate_limiter import ScrapeRateLimiter
from services.scraper.components.entity_extractor import EntityExtractor
from services.scraper.components.storage_handler import StorageHandler
from services.scraper.components.business_intel import (
    BusinessIntelligenceExtractor,
    BusinessIntelligence,
    ProductOffering,
    ServiceOffering,
    ValueProposition,
    TargetAudienceSignal,
    CompanyProfile,
)
from services.scraper.components.ner_extractor import (
    NERExtractor,
    ExtractedNamedEntities,
    NamedEntity,
    CompetitorDetector,
)

__all__ = [
    "URLQueueManager",
    "ContentParser",
    "ScrapeRateLimiter",
    "EntityExtractor",
    "StorageHandler",
    "BusinessIntelligenceExtractor",
    "BusinessIntelligence",
    "ProductOffering",
    "ServiceOffering",
    "ValueProposition",
    "TargetAudienceSignal",
    "CompanyProfile",
    "NERExtractor",
    "ExtractedNamedEntities",
    "NamedEntity",
    "CompetitorDetector",
]
