import logging
import time
from typing import Optional, Dict, Any
from backend.app.providers.base import LLMUsage, LLMRequest, LLMResponse

logger = logging.getLogger("marketai.providers.telemetry")

class LLMTelemetry:
    """
    Tracks and records real telemetry for all LLM gateway calls.
    Integrates with standard logging, Prometheus metrics, and CostService.
    """
    
    @staticmethod
    def record_call_success(
        provider: str,
        model: str,
        duration_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float
    ) -> None:
        logger.info(
            f"[LLM SUCCESS] Provider={provider} Model={model} "
            f"Latency={duration_ms}ms InTokens={prompt_tokens} OutTokens={completion_tokens} "
            f"Cost=${cost_usd:.6f}"
        )
        try:
            from backend.app.telemetry.metrics import telemetry_collector
            # Increment metric counters if available
            telemetry_collector.record_llm_call(
                provider=provider,
                model=model,
                status="success",
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd
            )
        except Exception:
            pass

    @staticmethod
    def record_call_failure(
        provider: str,
        model: str,
        error_type: str,
        error_message: str,
        duration_ms: int
    ) -> None:
        logger.warning(
            f"[LLM FAILURE] Provider={provider} Model={model} "
            f"ErrorType={error_type} Latency={duration_ms}ms Error='{error_message}'"
        )
        try:
            from backend.app.telemetry.metrics import telemetry_collector
            telemetry_collector.record_llm_call(
                provider=provider,
                model=model,
                status="failure",
                duration_ms=duration_ms,
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=0.0
            )
        except Exception:
            pass

    @staticmethod
    def record_provider_fallback(
        original_provider: str,
        fallback_provider: str,
        reason: str
    ) -> None:
        logger.warning(
            f"[LLM FALLBACK] Falling back from {original_provider} to {fallback_provider}. Reason: {reason}"
        )

llm_telemetry = LLMTelemetry()
