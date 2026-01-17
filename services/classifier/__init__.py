"""
Prompt Classifier Engine.

Classifies prompts with intent metadata for accurate simulation targeting.
"""

from services.classifier.classifier import (
    PromptClassifier,
    ClassificationError,
    get_classifications_for_website,
)
from services.classifier.schemas import (
    IntentType,
    FunnelStage,
    QueryIntent,
    UserIntent,
    ClassificationResult,
    ClassificationSummary,
)

__all__ = [
    "PromptClassifier",
    "ClassificationError",
    "get_classifications_for_website",
    "IntentType",
    "FunnelStage",
    "QueryIntent",
    "UserIntent",
    "ClassificationResult",
    "ClassificationSummary",
]
