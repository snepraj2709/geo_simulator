"""
Enum definitions for the LLM Brand Monitor.

All enums inherit from str and Enum for JSON serialization compatibility.
"""

from enum import Enum


class WebsiteStatus(str, Enum):
    """Website scraping status."""

    PENDING = "pending"
    SCRAPING = "scraping"
    COMPLETED = "completed"
    FAILED = "failed"


class PlanType(str, Enum):
    """Organization plan type."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, Enum):
    """User role within organization."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class BusinessModel(str, Enum):
    """Business model type for website analysis."""

    B2B = "b2b"
    B2C = "b2c"
    B2B2C = "b2b2c"
    MARKETPLACE = "marketplace"


class PageType(str, Enum):
    """Scraped page type classification."""

    HOMEPAGE = "homepage"
    PRODUCT = "product"
    SERVICE = "service"
    BLOG = "blog"
    ABOUT = "about"
    CONTACT = "contact"
    PRICING = "pricing"
    FAQ = "faq"
    OTHER = "other"


class IntentType(str, Enum):
    """User intent classification."""

    INFORMATIONAL = "informational"
    EVALUATION = "evaluation"
    DECISION = "decision"


class FunnelStage(str, Enum):
    """Marketing funnel stage."""

    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    PURCHASE = "purchase"


class QueryIntent(str, Enum):
    """Search query intent type."""

    COMMERCIAL = "Commercial"
    INFORMATIONAL = "Informational"
    NAVIGATIONAL = "Navigational"
    TRANSACTIONAL = "Transactional"


class PromptType(str, Enum):
    """Conversation prompt type."""

    PRIMARY = "primary"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"


class BrandPresence(str, Enum):
    """Brand presence state in LLM response."""

    IGNORED = "ignored"
    MENTIONED = "mentioned"
    TRUSTED = "trusted"
    RECOMMENDED = "recommended"
    COMPARED = "compared"


class BeliefType(str, Enum):
    """Type of belief installed by LLM response."""

    TRUTH = "truth"  # Epistemic clarity, neutrality
    SUPERIORITY = "superiority"  # Better than alternatives
    OUTCOME = "outcome"  # ROI, performance, results
    TRANSACTION = "transaction"  # Buy now, act
    IDENTITY = "identity"  # People like you use this
    SOCIAL_PROOF = "social_proof"  # Others chose this


class SimulationStatus(str, Enum):
    """Simulation run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMProviderEnum(str, Enum):
    """LLM provider identifiers."""

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"


class CompetitorRelationshipType(str, Enum):
    """Type of competitive relationship between brands."""

    DIRECT = "direct"  # Direct competitor in same market
    INDIRECT = "indirect"  # Indirect competitor, different approach
    SUBSTITUTE = "substitute"  # Alternative/substitute product
