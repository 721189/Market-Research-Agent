import logging
from typing import List, Dict, Any
from backend.app.providers.router import llm_gateway
from backend.app.providers.base import ExtractionResultState

logger = logging.getLogger("marketai.research.competitor")

def _validate_competitor_data(data: Any) -> bool:
    if not isinstance(data, list):
        return False
    # Each item must be a dictionary with a non-empty name
    for item in data:
        if not isinstance(item, dict) or not item.get("name"):
            return False
    return True

async def extract_competitors(product_idea: str, questions: List[str]) -> List[Dict[str, Any]]:
    """
    Stage 2: Competitor intelligence extractor.
    Uses LLM Gateway. Never returns synthetic fallback competitors upon failure.
    """
    prompt = f"""
    Perform deep competitor intelligence on: "{product_idea}".
    Target Questions: {questions}

    Extract real, verifiable market competitors or close industry alternatives.
    For each competitor, provide:
    - name: company or product name (e.g. "Linear", "Notion", "Stripe")
    - features: list of key product features
    - positioning: market positioning (e.g., Enterprise, Developer-first, SMB)
    - pricing: exact or estimated pricing structure
    - weaknesses: customer complaints, limitations, or gaps
    - sources: list of public domains or URLs

    Output JSON as a list of competitor objects:
    [
      {{
        "name": "...",
        "features": ["..."],
        "positioning": "...",
        "pricing": "...",
        "weaknesses": ["..."],
        "sources": ["..."]
      }}
    ]
    """

    res = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_competitor_data,
        timeout_seconds=35.0,
        max_retries=3
    )

    if res.state == ExtractionResultState.SUCCESS and isinstance(res.data, list):
        competitors = res.data
        for c in competitors:
            c["extraction_state"] = ExtractionResultState.SUCCESS.value
            c.setdefault("sources", [])
            c.setdefault("features", [])
            c.setdefault("weaknesses", [])
        return competitors
    elif res.state == ExtractionResultState.UNVERIFIED and isinstance(res.data, list):
        competitors = res.data
        for c in competitors:
            c["extraction_state"] = ExtractionResultState.UNVERIFIED.value
            c.setdefault("sources", [])
        return competitors
    else:
        logger.error(f"Competitor extraction failed for '{product_idea}': {res.error_message}")
        # Return empty list with transparent failure logging, NOT synthetic companies
        return []
