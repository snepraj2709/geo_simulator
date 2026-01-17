"""
Scraper components.

Based on ARCHITECTURE.md Website Scraper Service diagram:
- URL Queue Manager
- Content Parser
- Rate Limiter
- Entity Extractor
- Storage Handler
"""

from services.scraper.components.url_queue import URLQueueManager
from services.scraper.components.content_parser import ContentParser
from services.scraper.components.rate_limiter import ScrapeRateLimiter
from services.scraper.components.entity_extractor import EntityExtractor
from services.scraper.components.storage_handler import StorageHandler

__all__ = [
    "URLQueueManager",
    "ContentParser",
    "ScrapeRateLimiter",
    "EntityExtractor",
    "StorageHandler",
]
