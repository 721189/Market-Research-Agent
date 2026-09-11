import logging
from typing import List, Dict, Any
from backend.app.providers.router import llm_gateway
from backend.app.providers.base import ExtractionResultState

logger = logging.getLogger("marketai.research.pricing")

def _validate_pricing_data(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return "entry_tier_usd" in data or "mid_tier_usd" in data or "common_billing_models" in data

async def extract_pricing_landscape(product_idea: str, questions: List[str]) -> Dict[str, Any]:
    """
    Stage 2: Pricing landscape and willingness to pay analysis.
    Uses LLM Gateway. Never returns fake default pricing models upon failure.
    """
    prompt = f"""
    Analyze pricing models and willingness to pay for: "{product_idea}".
    Target Questions: {questions}

    Provide structured pricing benchmarks in valid JSON:
    {{
      "entry_tier_usd": float or null,
      "mid_tier_usd": float or null,
      "enterprise_tier_usd": float or null,
      "common_billing_models": ["subscription", "usage-based", etc.],
      "willingness_to_pay_signal": "Low" | "Moderate" | "High" | "Unknown",
      "sources": ["valid_domain_or_url"]
    }}
    """

    res = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_pricing_data,
        timeout_seconds=35.0,
        max_retries=3
    )

    if res.state == ExtractionResultState.SUCCESS and res.data:
        data = res.data
        data["extraction_state"] = ExtractionResultState.SUCCESS.value
        data.setdefault("sources", [])
        data.setdefault("common_billing_models", [])
        return data
    elif res.state == ExtractionResultState.UNVERIFIED and res.data:
        data = res.data
        data["extraction_state"] = ExtractionResultState.UNVERIFIED.value
        data.setdefault("sources", [])
        return data
    else:
        logger.error(f"Pricing extraction failed for '{product_idea}': {res.error_message}")
        return {
            "extraction_state": ExtractionResultState.FAILED.value,
            "error_message": res.error_message or "Failed to retrieve verified pricing data",
            "entry_tier_usd": None,
            "mid_tier_usd": None,
            "enterprise_tier_usd": None,
            "common_billing_models": [],
            "willingness_to_pay_signal": "Unknown",
            "sources": []
        }
