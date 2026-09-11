import logging
from typing import Dict, List, Any
from backend.app.providers.router import llm_gateway
from backend.app.providers.base import ExtractionResult, ExtractionResultState

logger = logging.getLogger("marketai.research.planner")

def _validate_plan_schema(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    required_keys = ["competitor_questions", "market_questions", "pricing_questions", "customer_questions"]
    return all(k in data and isinstance(data[k], list) and len(data[k]) > 0 for k in required_keys)

async def generate_research_plan(product_idea: str, mode: str = "quick") -> Dict[str, Any]:
    """
    Stage 1: Generate targeted research planning questions for competitor, market, pricing, and customer dimensions.
    Respects mode to keep Quick research lightweight and fast compared to Deep research.
    """
    max_q = 1 if mode in ("quick", "batch") else 3
    prompt = f"""
    You are an elite corporate strategy research planner.
    Analyze this product idea: "{product_idea}".
    Generate {max_q} specific, high-priority search question(s) across 4 dimensions:
    1. Competitor questions (who dominates, key alternatives)
    2. Market questions (TAM/SAM, core market drivers)
    3. Pricing questions (price tiers, monetization model)
    4. Customer questions (primary buyer persona, main pain point)

    Return valid JSON matching this exact structure:
    {{
      "competitor_questions": ["q1"],
      "market_questions": ["q1"],
      "pricing_questions": ["q1"],
      "customer_questions": ["q1"]
    }}
    """

    res: ExtractionResult[Dict[str, List[str]]] = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_plan_schema,
        timeout_seconds=20.0 if mode in ("quick", "batch") else 35.0,
        max_retries=2 if mode in ("quick", "batch") else 3
    )

    if res.state == ExtractionResultState.SUCCESS and res.data:
        return {
            "status": "SUCCESS",
            "competitor_questions": res.data.get("competitor_questions", [])[:max_q],
            "market_questions": res.data.get("market_questions", [])[:max_q],
            "pricing_questions": res.data.get("pricing_questions", [])[:max_q],
            "customer_questions": res.data.get("customer_questions", [])[:max_q],
        }

    logger.warning(f"LLM planning extraction resulted in state={res.state}: {res.error_message}. Using targeted query formulation.")
    # Deterministic query formulation derived strictly from the product idea (not fake data)
    return {
        "status": "PARTIAL",
        "error_message": res.error_message,
        "competitor_questions": [
            f"Who are the top direct and indirect competitors for {product_idea}?",
            f"What are competitor features, weaknesses, and pricing regarding {product_idea}?"
        ],
        "market_questions": [
            f"What is the total addressable market size (TAM) and projected CAGR for {product_idea}?",
            f"What key industry trends and regulatory headwinds affect {product_idea}?"
        ],
        "pricing_questions": [
            f"What is the current retail pricing range and business model for {product_idea}?",
            f"What are customer price thresholds and expected margins for {product_idea}?"
        ],
        "customer_questions": [
            f"Who is the primary target demographic and customer persona for {product_idea}?",
            f"What are the biggest unsolved pain points for buyers of {product_idea}?"
        ]
    }
