"""
Google Gemini LLM client implementation.
"""

import time
from typing import Any

import google.generativeai as genai

from shared.config import settings
from shared.llm.base import LLMClient, LLMResponse


class GoogleClient(LLMClient):
    """Google Gemini API client."""

    provider = "google"

    def __init__(self, model: str = "gemini-pro"):
        self.model_name = model
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(model)

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using Google Gemini."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        start_time = time.perf_counter()

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        response = await self.model.generate_content_async(
            full_prompt,
            generation_config=generation_config,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return LLMResponse(
            text=response.text if response.text else "",
            model=self.model_name,
            provider=self.provider,
            tokens_used=0,  # Gemini doesn't expose token counts the same way
            latency_ms=latency_ms,
            raw_response={"text": response.text},
        )

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate chat completion using Google Gemini."""
        # Convert messages to Gemini format
        chat = self.model.start_chat(history=[])

        start_time = time.perf_counter()

        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        # Send all previous messages as context
        response = None
        for msg in messages:
            if msg["role"] == "user":
                response = await chat.send_message_async(
                    msg["content"],
                    generation_config=generation_config,
                )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        text = response.text if response and response.text else ""

        return LLMResponse(
            text=text,
            model=self.model_name,
            provider=self.provider,
            tokens_used=0,
            latency_ms=latency_ms,
            raw_response={"text": text},
        )
