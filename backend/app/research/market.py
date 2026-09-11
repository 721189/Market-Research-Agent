import logging
from typing import List, Dict, Any, Optional
from backend.app.providers.router import llm_gateway
from backend.app.providers.base import ExtractionResultState

logger = logging.getLogger("marketai.research.market")

def _validate_market_data(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    # Check if at least some quantitative or qualitative market fields exist
    has_tam = "tam_usd_billions" in data and isinstance(data["tam_usd_billions"], (int, float))
    has_tailwinds = "key_tailwinds" in data and isinstance(data["key_tailwinds"], list)
    return has_tam or has_tailwinds

async def extract_market_dynamics(product_idea: str, questions: List[str]) -> Dict[str, Any]:
    """
    Stage 2: Macroeconomic and industry market dynamics extractor.
    Uses LLM Gateway with real retries. Never converts failure into fake TAM/SAM data.
    """
    prompt = f"""
    Analyze the macroeconomic market dynamics for: "{product_idea}".
    Target Questions: {questions}

    Extract real market metrics if discoverable.
    Provide structured output in valid JSON:
    {{
      "tam_usd_billions": float or null,
      "sam_usd_billions": float or null,
      "som_usd_millions": float or null,
      "projected_cagr_percentage": float or null,
      "key_tailwinds": ["trend 1", "trend 2"],
      "key_headwinds": ["risk 1", "risk 2"],
      "sources": ["valid_source_url_or_domain_1"]
    }}
    """

    res = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_market_data,
        timeout_seconds=35.0,
        max_retries=3
    )

    if res.state == ExtractionResultState.SUCCESS and res.data:
        data = res.data
        data["extraction_state"] = ExtractionResultState.SUCCESS.value
        data["provider_used"] = res.provider_used
        data["model_used"] = res.model_used
        data.setdefault("sources", [])
        return data
    elif res.state == ExtractionResultState.UNVERIFIED and res.data:
        data = res.data
        data["extraction_state"] = ExtractionResultState.UNVERIFIED.value
        data["error_message"] = res.error_message
        data.setdefault("sources", [])
        return data
    else:
        # Transparent failure: never fabricate fake market figures
        logger.error(f"Market dynamics extraction failed for '{product_idea}': {res.error_message}")
        return {
            "extraction_state": ExtractionResultState.FAILED.value,
            "error_message": res.error_message or "Failed to retrieve verified market dynamics from providers",
            "tam_usd_billions": None,
            "sam_usd_billions": None,
            "som_usd_millions": None,
            "projected_cagr_percentage": None,
            "key_tailwinds": [],
            "key_headwinds": [],
            "sources": []
        }
