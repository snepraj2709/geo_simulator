"""
Conversation Generator Service.

Generates realistic conversation topics and prompts for ICPs using LLM analysis.
"""

from services.conversation_generator.generator import (
    ConversationGenerator,
    ConversationGenerationError,
    get_conversations_for_icp,
    get_conversation_by_id,
)
from services.conversation_generator.schemas import (
    GeneratedConversation,
    GeneratedPrompt,
    ConversationGenerationResponse,
    PromptType,
)

__all__ = [
    "ConversationGenerator",
    "ConversationGenerationError",
    "get_conversations_for_icp",
    "get_conversation_by_id",
    "GeneratedConversation",
    "GeneratedPrompt",
    "ConversationGenerationResponse",
    "PromptType",
]
