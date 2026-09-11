from typing import Dict, Any, Optional, List
import contextvars
import time
import datetime
import logging
from decimal import Decimal

try:
    from sqlalchemy.orm import Session
    from backend.app.models.billing import UsageEvent, LLMCall
except ImportError:
    Session = Any # type: ignore
    UsageEvent = Any # type: ignore
    LLMCall = Any # type: ignore

logger = logging.getLogger("marketai.cost")

# Context variable to accumulate real tokens across all stages of a research job
_job_usage_context: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
    "job_usage_context", default=None
)

class UnpricedModelError(ValueError):
    """Raised when an unknown LLM model is encountered without configured pricing."""
    pass

class PriceCatalogEntry:
    def __init__(
        self,
        provider: str,
        model: str,
        effective_from: datetime.datetime,
        input_price_per_million: float,
        output_price_per_million: float,
        search_price_per_call: float = 0.005,
        is_unpriced: bool = False
    ):
        self.provider = provider
        self.model = model
        self.effective_from = effective_from
        self.input_price_per_million = input_price_per_million
        self.output_price_per_million = output_price_per_million
        self.search_price_per_call = search_price_per_call
        self.is_unpriced = is_unpriced

class CostService:
    """
    Authoritative LLM token metering, versioned price catalog, and reproducible cost auditing.
    Supports versioned pricing schemas with effective dates.
    """
    
    PRICE_CATALOG: List[PriceCatalogEntry] = [
        PriceCatalogEntry(
            provider="google-gemini",
            model="gemini-1.5-flash",
            effective_from=datetime.datetime(2024, 1, 1),
            input_price_per_million=0.075,
            output_price_per_million=0.30,
            search_price_per_call=0.005
        ),
        PriceCatalogEntry(
            provider="google-gemini",
            model="gemini-1.5-pro",
            effective_from=datetime.datetime(2024, 1, 1),
            input_price_per_million=1.25,
            output_price_per_million=5.00,
            search_price_per_call=0.005
        ),
        PriceCatalogEntry(
            provider="google-gemini",
            model="gemini-2.0-flash",
            effective_from=datetime.datetime(2025, 1, 1),
            input_price_per_million=0.10,
            output_price_per_million=0.40,
            search_price_per_call=0.005
        ),
        PriceCatalogEntry(
            provider="google-gemini",
            model="gemini-2.5-flash",
            effective_from=datetime.datetime(2025, 1, 1),
            input_price_per_million=0.10,
            output_price_per_million=0.40,
            search_price_per_call=0.005
        ),
        PriceCatalogEntry(
            provider="google-gemini",
            model="gemini-3.5-flash",
            effective_from=datetime.datetime(2026, 1, 1),
            input_price_per_million=0.15,
            output_price_per_million=0.60,
            search_price_per_call=0.005
        ),
    ]

    DEFAULT_SEARCH_PRICE = 0.005

    @classmethod
    def get_effective_pricing(
        cls,
        model: str,
        provider: str = "google-gemini",
        as_of: Optional[datetime.datetime] = None,
        raise_if_unknown: bool = True
    ) -> PriceCatalogEntry:
        check_date = as_of or datetime.datetime.utcnow()
        # Find matching entries effective before or on check_date, ordered by newest effective_from
        matching = [
            p for p in cls.PRICE_CATALOG 
            if (p.model == model or model.startswith(p.model)) and (provider == "any" or p.provider == provider) and p.effective_from <= check_date
        ]
        if matching:
            matching.sort(key=lambda p: p.effective_from, reverse=True)
            return matching[0]

        # Phase 29.2: Never silently price unknown models!
        if raise_if_unknown:
            logger.error(f"PRICING_ERROR: Model '{model}' from provider '{provider}' is not in price catalog.")
            raise UnpricedModelError(f"Model '{model}' is unknown and has no catalog pricing. Pricing error enforced.")

        return PriceCatalogEntry(
            provider=provider,
            model=model,
            effective_from=datetime.datetime(2024, 1, 1),
            input_price_per_million=0.0,
            output_price_per_million=0.0,
            search_price_per_call=0.0,
            is_unpriced=True
        )

    @classmethod
    def start_job_metering(
        cls,
        job_id: str,
        max_llm_calls: Optional[int] = None,
        max_context_tokens: Optional[int] = None
    ) -> None:
        """Initializes token and cost accumulator for a new research job execution."""
        _job_usage_context.set({
            "job_id": job_id,
            "max_llm_calls": max_llm_calls,
            "max_context_tokens": max_context_tokens,
            "models_used": {},
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "search_calls": 0,
            "start_time": time.time(),
            "llm_calls": 0,
            "call_records": []
        })

    @classmethod
    def record_llm_usage(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int = 0,
        provider: str = "google-gemini",
        success: bool = True,
        error_code: Optional[str] = None
    ) -> None:
        """Records actual tokens consumed by an LLM call."""
        ctx = _job_usage_context.get()
        if ctx is None:
            return

        ctx["total_input_tokens"] += max(0, input_tokens)
        ctx["total_output_tokens"] += max(0, output_tokens)
        ctx["llm_calls"] += 1

        cost = cls.calculate_cost(model, input_tokens, output_tokens, provider=provider)

        call_record = {
            "job_id": ctx.get("job_id"),
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": duration_ms,
            "success": success,
            "error_code": error_code,
            "estimated_cost": cost,
            "created_at": datetime.datetime.utcnow()
        }
        ctx["call_records"].append(call_record)

        models = ctx["models_used"]
        if model not in models:
            models[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "calls": 0,
                "duration_ms": 0
            }
        models[model]["input_tokens"] += max(0, input_tokens)
        models[model]["output_tokens"] += max(0, output_tokens)
        models[model]["calls"] += 1
        models[model]["duration_ms"] += duration_ms

    @classmethod
    def record_search_call(cls, count: int = 1) -> None:
        ctx = _job_usage_context.get()
        if ctx is not None:
            ctx["search_calls"] += count

    @classmethod
    def calculate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
        search_calls: int = 0,
        provider: str = "google-gemini",
        as_of: Optional[datetime.datetime] = None
    ) -> float:
        """Calculates exact USD cost based on the versioned price catalog."""
        pricing = cls.get_effective_pricing(model, provider=provider, as_of=as_of)
        input_cost = (max(0, input_tokens) / 1_000_000.0) * pricing.input_price_per_million
        output_cost = (max(0, output_tokens) / 1_000_000.0) * pricing.output_price_per_million
        search_cost = max(0, search_calls) * pricing.search_price_per_call
        return round(input_cost + output_cost + search_cost, 6)

    @classmethod
    def finalize_job_usage(
        cls,
        db: Optional[Session],
        org_id: str,
        job_id: str,
        default_model: str = "gemini-1.5-flash",
        user_id: Optional[str] = None
    ) -> Optional[UsageEvent]:
        """
        Finalizes the job's accumulated usage metrics and commits to database.
        Eliminates synthetic fallback values.
        """
        ctx = _job_usage_context.get()

        if ctx and ctx.get("job_id") == job_id:
            input_tokens = ctx["total_input_tokens"]
            output_tokens = ctx["total_output_tokens"]
            search_calls = ctx["search_calls"]
            duration_ms = int((time.time() - ctx["start_time"]) * 1000)
            
            if ctx["models_used"]:
                primary_model = max(
                    ctx["models_used"].keys(),
                    key=lambda m: ctx["models_used"][m]["input_tokens"] + ctx["models_used"][m]["output_tokens"]
                )
            else:
                primary_model = default_model

            # Persist individual discrete LLM calls
            if db:
                try:
                    for call in ctx.get("call_records", []):
                        llm_call_obj = LLMCall(
                            job_id=job_id,
                            org_id=org_id,
                            provider=call.get("provider", "google-gemini"),
                            model=call.get("model", primary_model),
                            input_tokens=call.get("input_tokens", 0),
                            output_tokens=call.get("output_tokens", 0),
                            latency_ms=call.get("latency_ms", 0),
                            attempt=1,
                            success=call.get("success", True),
                            error_code=call.get("error_code"),
                            estimated_cost=Decimal(str(call.get("estimated_cost", 0.0)))
                        )
                        db.add(llm_call_obj)
                except Exception as e:
                    logger.warning(f"Failed to record discrete LLMCall records: {e}")
        else:
            # Metering uninitialized
            logger.warning(f"METERING_ERROR: Context was not initialized for job {job_id}; recording zero tokens.")
            input_tokens = 0
            output_tokens = 0
            search_calls = 0
            duration_ms = 0
            primary_model = default_model

        estimated_cost = cls.calculate_cost(
            model=primary_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            search_calls=search_calls
        )

        logger.info(
            f"Job {job_id} finalized usage: In={input_tokens} Out={output_tokens} "
            f"Searches={search_calls} Cost=${estimated_cost:.6f} Duration={duration_ms}ms"
        )

        if db:
            try:
                usage_event = UsageEvent(
                    org_id=org_id,
                    job_id=job_id,
                    user_id=user_id,
                    provider="google-gemini",
                    model=primary_model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    search_calls=search_calls,
                    duration_ms=duration_ms,
                    estimated_cost_usd=Decimal(str(estimated_cost))
                )
                db.add(usage_event)
                db.commit()
                db.refresh(usage_event)
                return usage_event
            except Exception as e:
                logger.error(f"Failed to persist UsageEvent to database: {e}")
                db.rollback()
                return None

        return None

    @classmethod
    def finalize_and_persist(
        cls,
        db: Optional[Session],
        org_id: str,
        job_id: str,
        default_model: str = "gemini-1.5-flash",
        user_id: Optional[str] = None
    ) -> Optional[UsageEvent]:
        """Alias for finalize_job_usage for backward compatibility."""
        return cls.finalize_job_usage(
            db=db,
            org_id=org_id,
            job_id=job_id,
            default_model=default_model,
            user_id=user_id
        )

cost_service = CostService()
