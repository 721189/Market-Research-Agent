import os
import json
import time
import asyncio
import logging
from typing import Optional, Any, Dict

from backend.app.config import settings
from backend.app.providers.base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelUnavailableError
)
from backend.app.services.cost import cost_service
from backend.app.providers.telemetry import llm_telemetry

logger = logging.getLogger("marketai.providers.gemini")

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        self._client: Optional[Any] = None

    @property
    def provider_name(self) -> str:
        return "google-gemini"

    def _get_client(self) -> Any:
        """Lazy initialization of Google GenAI client."""
        if self._client is not None:
            return self._client

        api_key = self._api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise AuthenticationError("GEMINI_API_KEY is not configured in environment.", provider=self.provider_name)

        try:
            from google import genai
            self._client = genai.Client(api_key=api_key)
            return self._client
        except ImportError:
            logger.error("google-genai SDK is not installed in the current environment.")
            raise ProviderError("google-genai library not available in runtime", provider=self.provider_name, retryable=False)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            raise AuthenticationError(f"Gemini client initialization failed: {e}", provider=self.provider_name)

    def is_available(self) -> bool:
        key = self._api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        return bool(key)

    def _classify_and_raise_error(self, exc: Exception, model: str) -> None:
        err_msg = str(exc)
        lower_err = err_msg.lower()
        if "429" in lower_err or "quota" in lower_err or "resource_exhausted" in lower_err or "rate limit" in lower_err:
            raise RateLimitError(f"Gemini rate limit / quota exceeded on model '{model}': {err_msg}", provider=self.provider_name)
        elif "api_key" in lower_err or "unauthenticated" in lower_err or "permission_denied" in lower_err or "401" in lower_err or "403" in lower_err:
            raise AuthenticationError(f"Gemini authentication failed: {err_msg}", provider=self.provider_name)
        elif "not_found" in lower_err or "model" in lower_err and "not available" in lower_err:
            raise ModelUnavailableError(f"Gemini model '{model}' unavailable: {err_msg}", provider=self.provider_name)
        else:
            raise ProviderError(f"Gemini API call failed: {err_msg}", provider=self.provider_name, retryable=True)

    def _sync_generate(self, model_name: str, config_dict: Dict[str, Any], prompt: str) -> Any:
        client = self._get_client()
        try:
            from google.genai import types
            config = types.GenerateContentConfig(**config_dict)
            return client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
        except ImportError:
            # Direct dictionary config fallback if types not directly exported
            return client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config_dict
            )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        model_name = request.model or "gemini-1.5-flash"
        start_time = time.time()

        # Build config dictionary
        config_kwargs: Dict[str, Any] = {
            "temperature": request.temperature,
        }
        if request.system_instruction:
            config_kwargs["system_instruction"] = request.system_instruction
        if request.max_output_tokens:
            config_kwargs["max_output_tokens"] = request.max_output_tokens
        if request.response_mime_type == "application/json":
            config_kwargs["response_mime_type"] = "application/json"

        try:
            # Run in thread pool with strict timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(self._sync_generate, model_name, config_kwargs, request.prompt),
                timeout=request.timeout_seconds
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Extract real token usage
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

            cost_usd = cost_service.calculate_cost(
                model=model_name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens
            )

            # Record in CostService and Telemetry
            cost_service.record_llm_usage(
                model=model_name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                duration_ms=elapsed_ms
            )
            llm_telemetry.record_call_success(
                provider=self.provider_name,
                model=model_name,
                duration_ms=elapsed_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd
            )

            raw_text = response.text or ""
            parsed_json = None
            if request.response_mime_type == "application/json" and raw_text:
                try:
                    parsed_json = json.loads(raw_text)
                except json.JSONDecodeError as json_err:
                    logger.warning(f"Failed to parse JSON response from Gemini: {json_err}. Raw text: {raw_text[:200]}")

            usage = LLMUsage(
                provider=self.provider_name,
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                duration_ms=elapsed_ms,
                cost_usd=cost_usd
            )

            return LLMResponse(
                text=raw_text,
                parsed_json=parsed_json,
                provider=self.provider_name,
                model=model_name,
                usage=usage
            )

        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            llm_telemetry.record_call_failure(
                provider=self.provider_name,
                model=model_name,
                error_type="TIMEOUT",
                error_message=f"Gemini call timed out after {request.timeout_seconds}s",
                duration_ms=elapsed_ms
            )
            raise ProviderError(f"Gemini call timed out after {request.timeout_seconds}s", provider=self.provider_name, retryable=True)
        except Exception as exc:
            elapsed_ms = int((time.time() - start_time) * 1000)
            llm_telemetry.record_call_failure(
                provider=self.provider_name,
                model=model_name,
                error_type=type(exc).__name__,
                error_message=str(exc),
                duration_ms=elapsed_ms
            )
            self._classify_and_raise_error(exc, model_name)
