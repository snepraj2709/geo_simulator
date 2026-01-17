"""
Base LLM client interface.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar, Generic
from pydantic import BaseModel


class ResponseFormat(str, Enum):
    """Supported response formats."""
    TEXT = "text"
    JSON = "json"


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    text: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: int = 0
    raw_response: dict[str, Any] = field(default_factory=dict)
    parsed_json: dict[str, Any] | list | None = None

    @property
    def success(self) -> bool:
        return bool(self.text)

    def get_json(self) -> dict[str, Any] | list:
        """Parse and return JSON from response text."""
        if self.parsed_json is not None:
            return self.parsed_json

        # Try to parse the text as JSON
        text = self.text.strip()

        # Handle markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        self.parsed_json = json.loads(text.strip())
        return self.parsed_json

    def parse_as[T: BaseModel](self, model_class: type[T]) -> T:
        """Parse response as a Pydantic model."""
        data = self.get_json()
        return model_class.model_validate(data)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    provider: str = "base"

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: ResponseFormat = ResponseFormat.TEXT,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a completion for the given prompt.

        Args:
            prompt: User prompt to complete.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            response_format: Format for response (text or json).
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse with the generated text.
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: ResponseFormat = ResponseFormat.TEXT,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
            response_format: Format for response (text or json).
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse with the generated text.
        """
        pass

    async def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a JSON completion.

        Uses lower temperature for more deterministic JSON output.

        Args:
            prompt: User prompt to complete.
            system_prompt: Optional system prompt.
            temperature: Sampling temperature (default lower for JSON).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse with JSON in the text field.
        """
        return await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=ResponseFormat.JSON,
            **kwargs,
        )

    async def health_check(self) -> bool:
        """Check if the LLM service is available."""
        try:
            response = await self.complete("Hello", max_tokens=10)
            return response.success
        except Exception:
            return False
