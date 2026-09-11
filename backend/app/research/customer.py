import logging
from typing import List, Dict, Any
from backend.app.providers.router import llm_gateway
from backend.app.providers.base import ExtractionResultState

logger = logging.getLogger("marketai.research.customer")

def _validate_customer_data(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return "primary_persona" in data or "core_pain_points" in data

async def extract_customer_profiles(product_idea: str, questions: List[str]) -> Dict[str, Any]:
    """
    Stage 2: Target customer profiles, buyer persona, and pain point extractor.
    Uses LLM Gateway. Never returns fake default customer personas upon failure.
    """
    prompt = f"""
    Analyze customer demographics, ideal buyer personas, and pain points for: "{product_idea}".
    Target Questions: {questions}

    Provide structured output in valid JSON:
    {{
      "primary_persona": "Title / Target Role",
      "demographics": "Target demographic details",
      "core_pain_points": ["point 1", "point 2"],
      "buying_triggers": ["trigger 1", "trigger 2"],
      "sources": ["valid_domain_or_url"]
    }}
    """

    res = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_customer_data,
        timeout_seconds=35.0,
        max_retries=3
    )

    if res.state == ExtractionResultState.SUCCESS and res.data:
        data = res.data
        data["extraction_state"] = ExtractionResultState.SUCCESS.value
        data.setdefault("sources", [])
        data.setdefault("core_pain_points", [])
        data.setdefault("buying_triggers", [])
        return data
    elif res.state == ExtractionResultState.UNVERIFIED and res.data:
        data = res.data
        data["extraction_state"] = ExtractionResultState.UNVERIFIED.value
        data.setdefault("sources", [])
        return data
    else:
        logger.error(f"Customer extraction failed for '{product_idea}': {res.error_message}")
        return {
            "extraction_state": ExtractionResultState.FAILED.value,
            "error_message": res.error_message or "Failed to retrieve verified customer personas",
            "primary_persona": "Unidentified / Analysis Incomplete",
            "demographics": "Unknown",
            "core_pain_points": [],
            "buying_triggers": [],
            "sources": []
        }
