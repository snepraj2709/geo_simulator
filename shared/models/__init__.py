"""
Shared data models and SQLAlchemy ORM models.

This package contains all SQLAlchemy ORM models and Pydantic schemas
for the LLM Brand Monitor application.

Models are organized by domain:
- user: Organization and User models
- website: Website, ScrapedPage, WebsiteAnalysis
- icp: Ideal Customer Profile
- conversation: ConversationSequence, Prompt, PromptClassification
- simulation: SimulationRun, LLMResponse
- brand: Brand, LLMBrandState, LLMAnswerBeliefMap
- competitive: CompetitorRelationship, ShareOfVoice, SubstitutionPattern
"""

from shared.models.base import TimestampMixin, UUIDMixin
from shared.models.enums import (
    BeliefType,
    BrandPresence,
    BusinessModel,
    CompetitorRelationshipType,
    FunnelStage,
    IntentType,
    LLMProviderEnum,
    PageType,
    PlanType,
    PromptType,
    QueryIntent,
    SimulationStatus,
    UserRole,
    WebsiteStatus,
)
from shared.models.user import Organization, User
from shared.models.website import ScrapedPage, Website, WebsiteAnalysis
from shared.models.icp import ICP
from shared.models.conversation import ConversationSequence, Prompt, PromptClassification
from shared.models.simulation import LLMResponse, SimulationRun
from shared.models.brand import Brand, LLMAnswerBeliefMap, LLMBrandState
from shared.models.competitive import CompetitorRelationship, ShareOfVoice, SubstitutionPattern

__all__ = [
    # Mixins
    "TimestampMixin",
    "UUIDMixin",
    # Enums
    "BeliefType",
    "BrandPresence",
    "BusinessModel",
    "CompetitorRelationshipType",
    "FunnelStage",
    "IntentType",
    "LLMProviderEnum",
    "PageType",
    "PlanType",
    "PromptType",
    "QueryIntent",
    "SimulationStatus",
    "UserRole",
    "WebsiteStatus",
    # User models
    "Organization",
    "User",
    # Website models
    "Website",
    "ScrapedPage",
    "WebsiteAnalysis",
    # ICP models
    "ICP",
    # Conversation models
    "ConversationSequence",
    "Prompt",
    "PromptClassification",
    # Simulation models
    "SimulationRun",
    "LLMResponse",
    # Brand models
    "Brand",
    "LLMBrandState",
    "LLMAnswerBeliefMap",
    # Competitive analysis models
    "CompetitorRelationship",
    "ShareOfVoice",
    "SubstitutionPattern",
]
