import json
import logging
from typing import Dict, Any, List
from backend.app.providers.router import llm_gateway
from backend.app.providers.base import ExtractionResultState

logger = logging.getLogger("marketai.research.synthesis")

def _validate_synthesis_data(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return "executive_summary" in data or "strategic_recommendations" in data

async def synthesize_strategic_report(
    product_idea: str,
    competitors: List[Dict[str, Any]],
    market: Dict[str, Any],
    pricing: Dict[str, Any],
    customer: Dict[str, Any],
    financials: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 6: Strategic synthesis of research findings.
    Uses LLM Gateway. If synthesis fails, returns explicit FAILED state with diagnostic details.
    """
    context_data = {
        "product_idea": product_idea,
        "competitors": competitors,
        "market": market,
        "pricing": pricing,
        "customer": customer,
        "financials": financials
    }

    prompt = f"""
    You are an elite Strategy Consultant at a top-tier management firm (McKinsey/BCG).
    Based strictly on these validated research findings:
    {json.dumps(context_data, indent=2)}

    Generate a strategic synthesis in valid JSON format:
    {{
      "executive_summary": "Crisp 2-3 paragraph executive brief with verified data points",
      "strategic_recommendations": ["rec 1", "rec 2", "rec 3"],
      "swot_analysis": {{
        "strengths": ["s1", "s2"],
        "weaknesses": ["w1", "w2"],
        "opportunities": ["o1", "o2"],
        "threats": ["t1", "t2"]
      }},
      "go_to_market": {{
        "primary_channel": "channel name",
        "launch_timeline_weeks": int,
        "initial_focus": "focus description"
      }}
    }}
    """

    res = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_synthesis_data,
        timeout_seconds=45.0,
        max_retries=3
    )

    if res.state == ExtractionResultState.SUCCESS and res.data:
        data = res.data
        data["synthesis_state"] = ExtractionResultState.SUCCESS.value
        data.setdefault("strategic_recommendations", [])
        data.setdefault("swot_analysis", {})
        data.setdefault("go_to_market", {})
        return data
    elif res.state == ExtractionResultState.UNVERIFIED and res.data:
        data = res.data
        data["synthesis_state"] = ExtractionResultState.UNVERIFIED.value
        return data
    else:
        logger.error(f"Strategic synthesis generation failed: {res.error_message}")
        return {
            "synthesis_state": ExtractionResultState.FAILED.value,
            "error_message": res.error_message or "Failed to synthesize strategic management report",
            "executive_summary": f"Strategic synthesis could not be generated due to provider failure: {res.error_message}",
            "strategic_recommendations": [],
            "swot_analysis": {
                "strengths": [],
                "weaknesses": [],
                "opportunities": [],
                "threats": []
            },
            "go_to_market": {
                "primary_channel": "Unverified",
                "launch_timeline_weeks": None,
                "initial_focus": "Pending validated market input"
            }
        }
