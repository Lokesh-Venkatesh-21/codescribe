import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings

logger = logging.getLogger(__name__)

STRUCTURED_FIELDS = {
    "summary": "",
    "generated_docs": [],
    "changed_functions": [],
    "risks": [],
    "confidence_score": 0.5,
}


class BaseLLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate_json(self, prompt: str, fallback_context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class LocalFallbackProvider(BaseLLMProvider):
    name = "local_fallback"
    model = "deterministic"

    async def generate_json(self, prompt: str, fallback_context: dict[str, Any]) -> dict[str, Any]:
        del prompt
        return deterministic_fallback_payload(fallback_context)


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.llm_request_timeout_seconds
        self.max_retries = settings.llm_max_retries
        self._fallback = LocalFallbackProvider()

    async def generate_json(self, prompt: str, fallback_context: dict[str, Any]) -> dict[str, Any]:
        try:
            return await self._generate_json_with_retry(prompt)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Ollama generation failed; using deterministic fallback: %s", exc)
            return await self._fallback.generate_json(prompt, fallback_context)

    async def _generate_json_with_retry(self, prompt: str) -> dict[str, Any]:
        @retry(
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            stop=stop_after_attempt(self.max_retries),
            retry=retry_if_exception_type((httpx.HTTPError, ValueError)),
            reraise=True,
        )
        async def _call() -> dict[str, Any]:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2},
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            body = response.json()
            return normalize_structured_payload(body.get("response", ""))

        return await _call()


class GeminiProvider(BaseLLMProvider):
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self._fallback = LocalFallbackProvider()

    async def generate_json(self, prompt: str, fallback_context: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY missing; using deterministic fallback")
            return await self._fallback.generate_json(prompt, fallback_context)

        try:
            import google.generativeai as genai
        except ImportError:
            logger.warning("google-generativeai is not installed; using deterministic fallback")
            return await self._fallback.generate_json(prompt, fallback_context)

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = await model.generate_content_async(prompt)
        return normalize_structured_payload(response.text)


def build_llm_provider(settings: Settings) -> BaseLLMProvider:
    provider = settings.llm_provider.lower().strip()
    if provider == "gemini":
        return GeminiProvider(settings)
    if provider == "local_fallback":
        return LocalFallbackProvider()
    return OllamaProvider(settings)


def normalize_structured_payload(raw_response: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw_response, dict):
        parsed = raw_response
    else:
        parsed = _parse_json_response(raw_response)

    normalized = {**STRUCTURED_FIELDS, **parsed}
    normalized["generated_docs"] = _coerce_list(normalized.get("generated_docs"))
    normalized["changed_functions"] = _coerce_list(normalized.get("changed_functions"))
    normalized["risks"] = _coerce_list(normalized.get("risks"))
    normalized["confidence_score"] = _coerce_score(normalized.get("confidence_score"))
    normalized["summary"] = str(normalized.get("summary") or "")
    return normalized


def deterministic_fallback_payload(context: dict[str, Any]) -> dict[str, Any]:
    symbols = context.get("symbols", [])
    functions = [symbol["name"] for symbol in symbols if symbol.get("kind") == "function"]
    docs = []
    for symbol in symbols:
        docs.append(
            {
                "name": symbol.get("name", "unknown"),
                "kind": symbol.get("kind", "symbol"),
                "documentation": (
                    f"`{symbol.get('name', 'unknown')}` was detected in the changed code. "
                    "Review its behavior, inputs, outputs, and side effects before publishing."
                ),
            }
        )

    return {
        "summary": context.get(
            "summary",
            "CodeScribe generated a local documentation draft from PR diff and AST metadata.",
        ),
        "generated_docs": docs or ["No symbols were detected in the changed code."],
        "changed_functions": functions,
        "risks": ["LLM provider unavailable; deterministic local fallback was used."],
        "confidence_score": 0.55,
    }


def _parse_json_response(raw_response: str) -> dict[str, Any]:
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {cleaned[:200]}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON response must be an object")
    return parsed


def _coerce_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coerce_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, score))
