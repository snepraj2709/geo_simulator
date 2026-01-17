"""
LLM client factory.
"""

from enum import Enum
from typing import Type

from shared.llm.base import LLMClient
from shared.llm.openai_client import OpenAIClient
from shared.llm.anthropic_client import AnthropicClient
from shared.llm.google_client import GoogleClient


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    PERPLEXITY = "perplexity"


_CLIENT_MAP: dict[LLMProvider, Type[LLMClient]] = {
    LLMProvider.OPENAI: OpenAIClient,
    LLMProvider.ANTHROPIC: AnthropicClient,
    LLMProvider.GOOGLE: GoogleClient,
    # Perplexity uses OpenAI-compatible API
}


def get_llm_client(
    provider: LLMProvider | str,
    model: str | None = None,
) -> LLMClient:
    """
    Get an LLM client for the specified provider.

    Args:
        provider: The LLM provider to use.
        model: Optional model override.

    Returns:
        LLMClient instance for the provider.

    Raises:
        ValueError: If provider is not supported.
    """
    if isinstance(provider, str):
        provider = LLMProvider(provider)

    if provider == LLMProvider.PERPLEXITY:
        # Perplexity uses OpenAI-compatible API with different base URL
        from shared.config import settings
        from openai import AsyncOpenAI

        client = OpenAIClient(model=model or "llama-3.1-sonar-large-128k-online")
        client.client = AsyncOpenAI(
            api_key=settings.perplexity_api_key,
            base_url="https://api.perplexity.ai",
        )
        client.provider = "perplexity"
        return client

    client_class = _CLIENT_MAP.get(provider)
    if client_class is None:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    if model:
        return client_class(model=model)
    return client_class()


async def get_all_clients() -> dict[LLMProvider, LLMClient]:
    """Get clients for all configured providers."""
    from shared.config import settings

    clients: dict[LLMProvider, LLMClient] = {}

    if settings.openai_api_key:
        clients[LLMProvider.OPENAI] = get_llm_client(LLMProvider.OPENAI)

    if settings.anthropic_api_key:
        clients[LLMProvider.ANTHROPIC] = get_llm_client(LLMProvider.ANTHROPIC)

    if settings.google_api_key:
        clients[LLMProvider.GOOGLE] = get_llm_client(LLMProvider.GOOGLE)

    if settings.perplexity_api_key and settings.feature_perplexity_enabled:
        clients[LLMProvider.PERPLEXITY] = get_llm_client(LLMProvider.PERPLEXITY)

    return clients
