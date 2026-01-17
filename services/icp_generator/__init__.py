"""
ICP Generator Service.

Generates Ideal Customer Profiles using LLM analysis of website content.
"""

from services.icp_generator.generator import ICPGenerator, get_icps_for_website
from services.icp_generator.schemas import (
    GeneratedICP,
    ICPGenerationResponse,
    WebsiteContext,
)

__all__ = [
    "ICPGenerator",
    "get_icps_for_website",
    "GeneratedICP",
    "ICPGenerationResponse",
    "WebsiteContext",
]
