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

async def generate_research_plan(product_idea: str) -> Dict[str, Any]:
    """
    Stage 1: Generate targeted research planning questions for competitor, market, pricing, and customer dimensions.
    Returns structured plan with explicit extraction status.
    """
    prompt = f"""
    You are an elite corporate strategy research planner.
    Analyze this product idea: "{product_idea}".
    Generate specific search questions across 4 dimensions:
    1. Competitor questions (who dominates, features, weaknesses)
    2. Market questions (TAM, market trends, growth drivers)
    3. Pricing questions (price tiers, unit economics)
    4. Customer questions (buyer persona, pain points)

    Return valid JSON matching this exact structure:
    {{
      "competitor_questions": ["q1", "q2"],
      "market_questions": ["q1", "q2"],
      "pricing_questions": ["q1", "q2"],
      "customer_questions": ["q1", "q2"]
    }}
    """

    res: ExtractionResult[Dict[str, List[str]]] = await llm_gateway.generate_structured(
        prompt=prompt,
        model="gemini-1.5-flash",
        validator=_validate_plan_schema,
        timeout_seconds=30.0,
        max_retries=3
    )

    if res.state == ExtractionResultState.SUCCESS and res.data:
        return {
            "status": "SUCCESS",
            "competitor_questions": res.data.get("competitor_questions", []),
            "market_questions": res.data.get("market_questions", []),
            "pricing_questions": res.data.get("pricing_questions", []),
            "customer_questions": res.data.get("customer_questions", []),
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
