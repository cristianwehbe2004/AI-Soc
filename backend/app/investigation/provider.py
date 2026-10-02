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


class GoogleAIStudioProvider(LLMProvider):
    name = "google"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(
        self,
        settings: Settings,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        if not settings.llm_api_key:
            raise LLMProviderDisabledError("LLM_API_KEY is required for Google AI Studio")
        self.model = settings.llm_model
        self.max_output_tokens = settings.llm_max_output_tokens
        self.client = client or AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or self.default_base_url,
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
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": json.dumps(payload, separators=(",", ":"), default=str)},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_model.__name__.lower(),
                        "strict": True,
                        "schema": response_model.model_json_schema(),
                    },
                },
                max_tokens=self.max_output_tokens,
            )
        except Exception as exc:
            raise LLMProviderError(f"Google AI Studio response failed: {exc}") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMProviderError("Google AI Studio returned no structured output")
        try:
            output = response_model.model_validate_json(content)
        except Exception as exc:
            raise LLMProviderError("Google AI Studio returned invalid structured output") from exc
        usage = response.usage
        return ProviderResult(
            output=output,
            response_id=response.id,
            input_tokens=usage.prompt_tokens if usage is not None else 0,
            output_tokens=usage.completion_tokens if usage is not None else 0,
        )

    async def aclose(self) -> None:
        await self.client.close()


def build_llm_provider(settings: Settings) -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    if not settings.llm_enabled or provider_name == "disabled":
        raise LLMProviderDisabledError("AI investigation is disabled")
    if provider_name == "openai":
        return OpenAIProvider(settings)
    if provider_name in {"google", "google_ai_studio", "gemini"}:
        return GoogleAIStudioProvider(settings)
    raise LLMProviderError(f"Unsupported LLM provider: {settings.llm_provider}")
