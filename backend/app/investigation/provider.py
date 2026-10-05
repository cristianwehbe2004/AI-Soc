from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import Settings

OutputModel = TypeVar("OutputModel", bound=BaseModel)

GOOGLE_SUPPORTED_SCHEMA_KEYS = {
    "type",
    "enum",
    "items",
    "anyOf",
    "oneOf",
    "properties",
    "additionalProperties",
    "required",
}


def _google_json_schema(schema: dict) -> dict:
    """Reduce Pydantic JSON Schema to the subset accepted by Gemini."""
    schema = _inline_schema_refs(schema)
    cleaned: dict = {}
    for key, value in schema.items():
        if key not in GOOGLE_SUPPORTED_SCHEMA_KEYS:
            continue
        if key in {"properties", "$defs"}:
            cleaned[key] = {
                name: _google_json_schema(child)
                for name, child in value.items()
            }
        elif key == "items" and isinstance(value, dict):
            cleaned[key] = _google_json_schema(value)
        elif key in {"prefixItems", "anyOf", "oneOf"}:
            cleaned[key] = [
                _google_json_schema(child) if isinstance(child, dict) else child
                for child in value
            ]
        elif key == "additionalProperties" and isinstance(value, dict):
            cleaned[key] = _google_json_schema(value)
        else:
            cleaned[key] = value
    return cleaned


def _inline_schema_refs(schema: dict) -> dict:
    """Inline local definitions for Google's OpenAI compatibility endpoint."""
    definitions = schema.get("$defs", {})

    def resolve(value):
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if not isinstance(value, dict):
            return value
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            name = ref.removeprefix("#/$defs/")
            if name not in definitions:
                raise ValueError(f"Unknown local JSON Schema reference: {ref}")
            return resolve(definitions[name])
        return {
            key: resolve(child)
            for key, child in value.items()
            if key != "$defs"
        }

    return resolve(schema)


class LLMProviderError(RuntimeError):
    pass


class LLMProviderDisabledError(LLMProviderError):
    pass


class LLMProviderTransientError(LLMProviderError):
    """Raised for errors that are safe to retry: 5xx, network timeouts."""


class LLMProviderQuotaError(LLMProviderTransientError):
    """Raised for 429 rate-limit / quota-exceeded. Carries a retry_after hint (seconds)."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


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
    default_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

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
        
        # Sanitize base_url: strip trailing slashes to prevent double-slash 404 errors
        base_url = (settings.llm_base_url or self.default_base_url).rstrip("/")
        if not base_url.endswith("/openai"):
            base_url = f"{base_url}/openai"

        self.client = client or AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=base_url,
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
                        "schema": _google_json_schema(
                            response_model.model_json_schema()
                        ),
                    },
                },
                max_tokens=self.max_output_tokens,
                reasoning_effort="low",
            )
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower() or "rate_limit" in err_str.lower():
                # Parse retry_after from error if available
                retry_after = 60
                import re
                m = re.search(r"retry.?after[\":\s]+(\d+)", err_str, re.IGNORECASE)
                if m:
                    retry_after = int(m.group(1))
                raise LLMProviderQuotaError(
                    f"Google AI Studio quota/rate-limit: {exc}", retry_after=retry_after
                ) from exc
            if "404" in err_str or "NOT_FOUND" in err_str:
                raise LLMProviderError(
                    f"Google AI Studio 404 Error: Model '{self.model}' or endpoint not found. "
                    f"Ensure LLM_MODEL is a valid Gemini model (e.g. gemini-3.5-flash-lite) and "
                    f"LLM_API_KEY is a valid Google AI Studio key starting with 'AIzaSy...'. Error details: {exc}"
                ) from exc
            if any(code in err_str for code in ("500", "502", "503", "504")):
                raise LLMProviderTransientError(
                    f"Google AI Studio transient error: {exc}"
                ) from exc
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


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self.model = "mock-gemini-v1"

    async def generate_structured(
        self,
        *,
        instructions: str,
        payload: dict,
        response_model: type[OutputModel],
    ) -> ProviderResult[OutputModel]:
        import uuid
        model_name = response_model.__name__
        valid_refs = payload.get("valid_evidence_refs", [])
        refs_1 = valid_refs[:1] if valid_refs else []
        refs_2 = valid_refs[1:2] if len(valid_refs) > 1 else refs_1

        if model_name == "EvidenceAnalysis":
            mock_data = {
                "findings": [
                    {
                        "title": "Rapid Login Failures (Brute-Force Pattern)",
                        "severity": "high",
                        "confidence": 0.95,
                        "summary": "Observed multiple sequential authentication failures from target source IP.",
                        "evidence_refs": refs_1,
                    }
                ],
                "gaps": ["No endpoint EDR memory telemetry provided."],
                "uncertainties": ["Unclear if user credentials were stolen."],
            }
        elif model_name == "RiskAnalysis":
            mock_data = {
                "score": 85,
                "severity": "critical",
                "rationale": "Authentication failure burst combined with elevated role escalation.",
                "factors": ["Repeated login failure burst", "Privilege change event"],
            }
        elif model_name == "InvestigationNarrative":
            mock_data = {
                "executive_summary": "Automated security investigation completed. Attack pattern aligns with credential access and privilege escalation.",
                "attack_story": "An external entity initiated multiple authentication attempts before gaining access and attempting role elevation.",
                "confidence": 0.92,
            }
        elif model_name == "RecommendationSet":
            mock_data = {
                "recommendations": [
                    {
                        "title": "Revoke Compromised User Sessions",
                        "priority": "urgent",
                        "rationale": "Prevent unauthorized persistence after authentication burst.",
                        "actions": ["Revoke active refresh tokens", "Force password reset"],
                        "evidence_refs": refs_1,
                    },
                    {
                        "title": "Block Malicious Source IP",
                        "priority": "high",
                        "rationale": "Mitigate incoming brute force attempts.",
                        "actions": ["Add IP to perimeter blocklist"],
                        "evidence_refs": refs_2,
                    },
                ]
            }
        else:
            mock_data = {}

        output = response_model.model_validate(mock_data)
        return ProviderResult(
            output=output,
            response_id=f"mock-{uuid.uuid4().hex[:8]}",
            input_tokens=150,
            output_tokens=300,
        )



def build_llm_provider(settings: Settings) -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    if not settings.llm_enabled or provider_name == "disabled":
        raise LLMProviderDisabledError("AI investigation is disabled")
    if provider_name == "openai":
        return OpenAIProvider(settings)
    if provider_name in {"google", "google_ai_studio", "gemini"}:
        return GoogleAIStudioProvider(settings)
    if provider_name == "mock":
        return MockProvider(settings)
    raise LLMProviderError(f"Unsupported LLM provider: {settings.llm_provider}")
