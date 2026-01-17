"""
OpenAI LLM client implementation.
"""

import time
from typing import Any

from openai import AsyncOpenAI

from shared.config import settings
from shared.llm.base import LLMClient, LLMResponse, ResponseFormat


class OpenAIClient(LLMClient):
    """OpenAI API client."""

    provider = "openai"

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: ResponseFormat = ResponseFormat.TEXT,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using OpenAI."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self.chat(messages, temperature, max_tokens, response_format, **kwargs)

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: ResponseFormat = ResponseFormat.TEXT,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate chat completion using OpenAI."""
        start_time = time.perf_counter()

        # Build request parameters
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add JSON mode if requested
        if response_format == ResponseFormat.JSON:
            create_kwargs["response_format"] = {"type": "json_object"}

        # Merge additional kwargs
        create_kwargs.update(kwargs)

        response = await self.client.chat.completions.create(**create_kwargs)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return LLMResponse(
            text=response.choices[0].message.content or "",
            model=response.model,
            provider=self.provider,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            latency_ms=latency_ms,
            raw_response=response.model_dump(),
        )
