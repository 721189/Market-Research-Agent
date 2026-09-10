import json
import os
from typing import Dict, List, Any
from google import genai
from backend.app.config import settings

def get_gemini_client():
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

async def generate_research_plan(product_idea: str) -> Dict[str, List[str]]:
    """
    Stage 1: Generate research planning questions for competitor, market, pricing, and customer dimensions.
    """
    client = get_gemini_client()
    if not client:
        # High quality heuristic fallback
        return {
            "competitor_questions": [
                f"Who are the top direct and indirect competitors for {product_idea}?",
                f"What are competitor features, weaknesses, and customer complaints regarding {product_idea}?"
            ],
            "market_questions": [
                f"What is the total addressable market size and projected CAGR for {product_idea}?",
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
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return data
    except Exception:
        return {
            "competitor_questions": [f"Top competitors for {product_idea}"],
            "market_questions": [f"Market size for {product_idea}"],
            "pricing_questions": [f"Pricing models for {product_idea}"],
            "customer_questions": [f"Target customers for {product_idea}"]
        }
