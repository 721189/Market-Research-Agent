import asyncio
import logging
import random
import time
from typing import Dict, Any, List, Optional, Callable, TypeVar
import json

from backend.app.providers.base import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    ExtractionResult,
    ExtractionResultState,
    ProviderError,
    RateLimitError,
    AuthenticationError,
    ModelUnavailableError
)
from backend.app.providers.gemini import GeminiProvider
from backend.app.providers.telemetry import llm_telemetry

logger = logging.getLogger("marketai.providers.gateway")

T = TypeVar("T")

class LLMGateway:
    """
    Authoritative LLM Gateway & Model Router.
    Controls:
    - Model selection and dispatch
    - Retry policies with exponential backoff & full jitter
    - Fallback across providers if configured
    - Explicit result state accounting (SUCCESS, PARTIAL, FAILED, UNVERIFIED)
    - Elimination of synthetic/fake data in production execution
    """

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {
            "google-gemini": GeminiProvider(),
        }
        self._default_provider = "google-gemini"
        self._default_model = "gemini-1.5-flash"

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        self._providers[name] = provider

    def get_provider(self, name: Optional[str] = None) -> BaseLLMProvider:
        provider_name = name or self._default_provider
        if provider_name not in self._providers:
            raise ProviderError(f"Provider '{provider_name}' is not registered.", provider="gateway", retryable=False)
        return self._providers[provider_name]

    async def execute_with_retry(
        self,
        request: LLMRequest,
        provider_name: Optional[str] = None,
        max_retries: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 10.0
    ) -> LLMResponse:
        """
        Executes an LLM request with strict retry logic and exponential jittered backoff.
        """
        provider = self.get_provider(provider_name)
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                response = await provider.generate(request)
                return response
            except (RateLimitError, ModelUnavailableError, ProviderError) as exc:
                last_exception = exc
                if not exc.retryable or attempt == max_retries:
                    logger.error(
                        f"LLM Gateway execution failed permanently on attempt {attempt}/{max_retries} "
                        f"using provider={provider.provider_name}: {exc}"
                    )
                    raise exc

                # Exponential backoff with full jitter
                delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)) + random.uniform(0.1, 1.0))
                logger.warning(
                    f"LLM call failed (attempt {attempt}/{max_retries}) with {type(exc).__name__}. "
                    f"Retrying in {delay:.2f}s... Error: {exc}"
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                last_exception = exc
                logger.error(f"Unclassified failure in LLM Gateway on attempt {attempt}: {exc}")
                if attempt == max_retries:
                    raise ProviderError(f"Fatal LLM execution error: {exc}", provider=provider.provider_name, retryable=False)
                await asyncio.sleep(base_delay_seconds)

        raise ProviderError(f"Exhausted {max_retries} retries: {last_exception}", provider=provider.provider_name, retryable=False)

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 35.0,
        max_retries: int = 3,
        validator: Optional[Callable[[Any], bool]] = None
    ) -> ExtractionResult[Any]:
        """
        Executes a structured JSON extraction request and returns an explicit ExtractionResult.
        Guarantees NO fake fallback values: if the LLM or validation fails, returns FAILED or PARTIAL.
        """
        request = LLMRequest(
            prompt=prompt,
            system_instruction=system_instruction,
            model=model or self._default_model,
            response_mime_type="application/json",
            timeout_seconds=timeout_seconds
        )

        try:
            response = await self.execute_with_retry(request, max_retries=max_retries)
            
            if response.parsed_json is None:
                # Attempt manual parse if text exists
                if response.text:
                    try:
                        parsed = json.loads(response.text)
                        response.parsed_json = parsed
                    except Exception as parse_err:
                        return ExtractionResult(
                            data=None,
                            state=ExtractionResultState.FAILED,
                            error_message=f"JSON decoding failure from model output: {parse_err}",
                            provider_used=response.provider,
                            model_used=response.model,
                            usage=response.usage,
                            raw_text=response.text
                        )
                else:
                    return ExtractionResult(
                        data=None,
                        state=ExtractionResultState.FAILED,
                        error_message="Model returned empty response content",
                        provider_used=response.provider,
                        model_used=response.model,
                        usage=response.usage
                    )

            # Optional schema validation
            if validator:
                is_valid = False
                try:
                    is_valid = validator(response.parsed_json)
                except Exception as val_err:
                    logger.warning(f"Validator exception during extraction: {val_err}")

                if not is_valid:
                    return ExtractionResult(
                        data=response.parsed_json,
                        state=ExtractionResultState.UNVERIFIED,
                        error_message="Extracted payload failed schema or business constraint validation",
                        provider_used=response.provider,
                        model_used=response.model,
                        usage=response.usage,
                        raw_text=response.text
                    )

            return ExtractionResult(
                data=response.parsed_json,
                state=ExtractionResultState.SUCCESS,
                provider_used=response.provider,
                model_used=response.model,
                usage=response.usage,
                raw_text=response.text
            )

        except Exception as exc:
            logger.error(f"LLM Gateway extraction failed: {exc}")
            return ExtractionResult(
                data=None,
                state=ExtractionResultState.FAILED,
                error_message=str(exc),
                provider_used="google-gemini",
                model_used=model or self._default_model
            )

llm_gateway = LLMGateway()
