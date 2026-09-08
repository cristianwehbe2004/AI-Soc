from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import Settings

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class LLMProviderError(RuntimeError):
    pass


class LLMProviderDisabledError(LLMProviderError):
    pass


@dataclass(frozen=True)
class ProviderResult(Generic[OutputModel]):
    output: OutputModel
    response_id: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate_structured(
        self,
        *,
        instructions: str,
        payload: dict,
        response_model: type[OutputModel],
    ) -> ProviderResult[OutputModel]:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        settings: Settings,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        if not settings.llm_api_key:
            raise LLMProviderDisabledError("LLM_API_KEY is required for OpenAI")
        self.model = settings.llm_model
        self.max_output_tokens = settings.llm_max_output_tokens
        self.client = client or AsyncOpenAI(
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )

    async def generate_structured(
        self,
        *,
        instructions: str,
        payload: dict,
        response_model: type[OutputModel],
    ) -> ProviderResult[OutputModel]:
        try:
            response = await self.client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=json.dumps(payload, separators=(",", ":"), default=str),
                text_format=response_model,
                max_output_tokens=self.max_output_tokens,
                store=False,
            )
        except Exception as exc:
            raise LLMProviderError(f"OpenAI response failed: {exc}") from exc

        output = response.output_parsed
        if output is None:
            raise LLMProviderError("OpenAI returned no structured output")
        usage = response.usage
        return ProviderResult(
            output=output,
            response_id=response.id,
            input_tokens=usage.input_tokens if usage is not None else 0,
            output_tokens=usage.output_tokens if usage is not None else 0,
        )

    async def aclose(self) -> None:
        await self.client.close()


def build_llm_provider(settings: Settings) -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    if not settings.llm_enabled or provider_name == "disabled":
        raise LLMProviderDisabledError("AI investigation is disabled")
    if provider_name == "openai":
        return OpenAIProvider(settings)
    raise LLMProviderError(f"Unsupported LLM provider: {settings.llm_provider}")
