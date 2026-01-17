"""
LLM Provider Adapters.

Wraps the shared LLM clients with simulation-specific functionality,
including retry logic, error handling, and metrics collection.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.config import settings
from shared.llm.base import LLMClient, LLMResponse as BaseLLMResponse
from shared.llm.factory import get_llm_client, LLMProvider
from shared.utils.logging import get_logger

from services.simulation.schemas import (
    LLMProviderType,
    LLMQueryRequest,
    LLMQueryResponse,
    RateLimitConfig,
)

logger = get_logger(__name__)


class BaseLLMAdapter(ABC):
    """
    Base class for LLM provider adapters.

    Provides common functionality for all LLM adapters including:
    - Retry logic with exponential backoff
    - Error handling and normalization
    - Metrics collection
    - Rate limit awareness
    """

    provider: LLMProviderType
    default_model: str
    rate_limit_config: RateLimitConfig

    def __init__(
        self,
        model: str | None = None,
        rate_limit_config: RateLimitConfig | None = None,
    ):
        """
        Initialize the adapter.

        Args:
            model: Model to use, defaults to provider's default.
            rate_limit_config: Rate limiting configuration.
        """
        self.model = model or self.default_model
        self.rate_limit_config = rate_limit_config or RateLimitConfig()

        # Metrics tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._total_tokens = 0
        self._total_latency_ms = 0

        # Get the underlying LLM client
        self._client: LLMClient | None = None

    @property
    def client(self) -> LLMClient:
        """Get or create the LLM client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    @abstractmethod
    def _create_client(self) -> LLMClient:
        """Create the underlying LLM client."""
        pass

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for simulation queries."""
        pass

    async def query(self, request: LLMQueryRequest) -> LLMQueryResponse:
        """
        Query the LLM provider with retry logic.

        Args:
            request: The query request.

        Returns:
            Normalized query response.
        """
        self._total_requests += 1
        start_time = time.perf_counter()

        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type((Exception,)),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=30),
            ):
                with attempt:
                    response = await self._execute_query(request)

                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    self._successful_requests += 1
                    self._total_tokens += response.tokens_used
                    self._total_latency_ms += latency_ms

                    logger.info(
                        "LLM query successful",
                        provider=self.provider.value,
                        model=self.model,
                        tokens=response.tokens_used,
                        latency_ms=latency_ms,
                    )

                    return response

        except Exception as e:
            self._failed_requests += 1
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            logger.error(
                "LLM query failed",
                provider=self.provider.value,
                model=self.model,
                error=str(e),
                latency_ms=latency_ms,
            )

            return LLMQueryResponse(
                provider=self.provider,
                model=self.model,
                response_text="",
                tokens_used=0,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

        # This shouldn't be reached, but just in case
        return LLMQueryResponse(
            provider=self.provider,
            model=self.model,
            response_text="",
            success=False,
            error="Unknown error",
        )

    async def _execute_query(self, request: LLMQueryRequest) -> LLMQueryResponse:
        """
        Execute the actual LLM query.

        Args:
            request: The query request.

        Returns:
            Query response.
        """
        system_prompt = request.system_prompt or self._get_system_prompt()

        response: BaseLLMResponse = await self.client.complete(
            prompt=request.prompt_text,
            system_prompt=system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return LLMQueryResponse(
            provider=self.provider,
            model=response.model,
            response_text=response.text,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
            success=response.success,
            raw_response=response.raw_response,
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get adapter metrics."""
        return {
            "provider": self.provider.value,
            "model": self.model,
            "total_requests": self._total_requests,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "total_tokens": self._total_tokens,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": (
                self._total_latency_ms / self._successful_requests
                if self._successful_requests > 0
                else 0
            ),
            "avg_tokens": (
                self._total_tokens / self._successful_requests
                if self._successful_requests > 0
                else 0
            ),
            "success_rate": (
                self._successful_requests / self._total_requests
                if self._total_requests > 0
                else 0
            ),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._total_tokens = 0
        self._total_latency_ms = 0

    async def health_check(self) -> bool:
        """Check if the provider is available."""
        try:
            return await self.client.health_check()
        except Exception:
            return False


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI GPT models."""

    provider = LLMProviderType.OPENAI
    default_model = "gpt-4o"

    def _create_client(self) -> LLMClient:
        return get_llm_client(LLMProvider.OPENAI, self.model)

    def _get_system_prompt(self) -> str:
        return """You are a helpful assistant answering questions about products and services.
When recommending or discussing brands, products, or companies:
- Be informative and balanced
- Mention relevant alternatives when appropriate
- Provide context for your recommendations
- Be honest about pros and cons"""


class GoogleAdapter(BaseLLMAdapter):
    """Adapter for Google Gemini models."""

    provider = LLMProviderType.GOOGLE
    default_model = "gemini-1.5-flash"

    def _create_client(self) -> LLMClient:
        return get_llm_client(LLMProvider.GOOGLE, self.model)

    def _get_system_prompt(self) -> str:
        return """You are a helpful assistant answering questions about products and services.
When recommending or discussing brands, products, or companies:
- Be informative and balanced
- Mention relevant alternatives when appropriate
- Provide context for your recommendations
- Be honest about pros and cons"""


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude models."""

    provider = LLMProviderType.ANTHROPIC
    default_model = "claude-3-5-sonnet-20241022"

    def _create_client(self) -> LLMClient:
        return get_llm_client(LLMProvider.ANTHROPIC, self.model)

    def _get_system_prompt(self) -> str:
        return """You are a helpful assistant answering questions about products and services.
When recommending or discussing brands, products, or companies:
- Be informative and balanced
- Mention relevant alternatives when appropriate
- Provide context for your recommendations
- Be honest about pros and cons"""


class PerplexityAdapter(BaseLLMAdapter):
    """Adapter for Perplexity models."""

    provider = LLMProviderType.PERPLEXITY
    default_model = "llama-3.1-sonar-large-128k-online"

    def _create_client(self) -> LLMClient:
        return get_llm_client(LLMProvider.PERPLEXITY, self.model)

    def _get_system_prompt(self) -> str:
        return """You are a helpful assistant answering questions about products and services.
When recommending or discussing brands, products, or companies:
- Be informative and balanced
- Mention relevant alternatives when appropriate
- Provide context for your recommendations
- Be honest about pros and cons
- Cite sources when available"""


class LLMAdapterFactory:
    """
    Factory for creating LLM adapters.

    Provides a centralized way to create and manage LLM adapters
    with proper configuration and caching.
    """

    _adapters: dict[LLMProviderType, type[BaseLLMAdapter]] = {
        LLMProviderType.OPENAI: OpenAIAdapter,
        LLMProviderType.GOOGLE: GoogleAdapter,
        LLMProviderType.ANTHROPIC: AnthropicAdapter,
        LLMProviderType.PERPLEXITY: PerplexityAdapter,
    }

    _instances: dict[str, BaseLLMAdapter] = {}

    @classmethod
    def get_adapter(
        cls,
        provider: LLMProviderType,
        model: str | None = None,
        rate_limit_config: RateLimitConfig | None = None,
    ) -> BaseLLMAdapter:
        """
        Get an adapter for the specified provider.

        Args:
            provider: The LLM provider type.
            model: Optional model override.
            rate_limit_config: Optional rate limiting config.

        Returns:
            LLM adapter instance.

        Raises:
            ValueError: If provider is not supported.
        """
        adapter_class = cls._adapters.get(provider)
        if adapter_class is None:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        # Create cache key
        cache_key = f"{provider.value}:{model or 'default'}"

        # Return cached instance or create new one
        if cache_key not in cls._instances:
            cls._instances[cache_key] = adapter_class(
                model=model,
                rate_limit_config=rate_limit_config,
            )

        return cls._instances[cache_key]

    @classmethod
    def get_available_adapters(cls) -> list[BaseLLMAdapter]:
        """
        Get adapters for all configured providers.

        Returns:
            List of available adapters.
        """
        adapters = []

        if settings.openai_api_key:
            adapters.append(cls.get_adapter(LLMProviderType.OPENAI))

        if settings.google_api_key:
            adapters.append(cls.get_adapter(LLMProviderType.GOOGLE))

        if settings.anthropic_api_key:
            adapters.append(cls.get_adapter(LLMProviderType.ANTHROPIC))

        if settings.perplexity_api_key and settings.feature_perplexity_enabled:
            adapters.append(cls.get_adapter(LLMProviderType.PERPLEXITY))

        return adapters

    @classmethod
    def get_adapters_for_providers(
        cls,
        providers: list[LLMProviderType],
    ) -> list[BaseLLMAdapter]:
        """
        Get adapters for specific providers.

        Args:
            providers: List of provider types.

        Returns:
            List of adapters.
        """
        return [cls.get_adapter(p) for p in providers]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the adapter instance cache."""
        cls._instances.clear()

    @classmethod
    async def health_check_all(cls) -> dict[str, bool]:
        """
        Check health of all available adapters.

        Returns:
            Dict mapping provider names to health status.
        """
        adapters = cls.get_available_adapters()
        results = await asyncio.gather(
            *[adapter.health_check() for adapter in adapters],
            return_exceptions=True,
        )

        return {
            adapter.provider.value: (
                result if isinstance(result, bool) else False
            )
            for adapter, result in zip(adapters, results)
        }
