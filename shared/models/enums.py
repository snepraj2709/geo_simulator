"""
Enum definitions for the LLM Brand Monitor.
"""

from enum import Enum


class WebsiteStatus(str, Enum):
    """Website scraping status."""

    PENDING = "pending"
    SCRAPING = "scraping"
    COMPLETED = "completed"
    FAILED = "failed"


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
