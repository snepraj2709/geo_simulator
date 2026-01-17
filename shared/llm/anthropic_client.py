"""
Anthropic (Claude) LLM client implementation.
"""

import time
from typing import Any

from anthropic import AsyncAnthropic

from shared.config import settings
from shared.llm.base import LLMClient, LLMResponse, ResponseFormat


# JSON mode instruction to append for Claude
JSON_INSTRUCTION = """

IMPORTANT: Your response must be valid JSON only. Do not include any text before or after the JSON.
Do not use markdown code blocks. Output raw JSON starting with { or [."""


class AnthropicClient(LLMClient):
    """Anthropic Claude API client."""

    provider = "anthropic"

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: ResponseFormat = ResponseFormat.TEXT,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using Anthropic."""
        # For JSON mode, append instruction to prompt
        if response_format == ResponseFormat.JSON:
            prompt = prompt + JSON_INSTRUCTION

        messages = [{"role": "user", "content": prompt}]
        return await self.chat(
            messages,
            temperature,
            max_tokens,
            response_format=response_format,
            system_prompt=system_prompt,
            **kwargs,
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: ResponseFormat = ResponseFormat.TEXT,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate chat completion using Anthropic."""
        start_time = time.perf_counter()

        # For JSON mode, enhance system prompt
        effective_system = system_prompt or ""
        if response_format == ResponseFormat.JSON:
            effective_system = (effective_system + JSON_INSTRUCTION).strip()

        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if effective_system:
            create_kwargs["system"] = effective_system

        response = await self.client.messages.create(**create_kwargs, **kwargs)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        return LLMResponse(
            text=text,
            model=response.model,
            provider=self.provider,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            latency_ms=latency_ms,
            raw_response=response.model_dump(),
        )
