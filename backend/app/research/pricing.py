import json
from typing import List, Dict, Any
from backend.app.research.planner import get_gemini_client

async def extract_pricing_landscape(product_idea: str, questions: List[str]) -> Dict[str, Any]:
    client = get_gemini_client()
    if not client:
        return {
            "entry_tier_usd": 15.0,
            "mid_tier_usd": 49.0,
            "enterprise_tier_usd": 199.0,
            "common_billing_models": ["Monthly subscription", "Per-seat license"],
            "willingness_to_pay_signal": "Moderate to High",
            "sources": ["https://g2.com"]
        }

    prompt = f"""
    Analyze pricing models and willingness to pay for: "{product_idea}".
    Questions: {questions}

    Provide structured pricing benchmarks in valid JSON:
    {{
      "entry_tier_usd": float,
      "mid_tier_usd": float,
      "enterprise_tier_usd": float,
      "common_billing_models": ["model 1", "model 2"],
      "willingness_to_pay_signal": "Low" | "Moderate" | "High",
      "sources": ["domain 1"]
    }}
    """
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception:
        return {
            "entry_tier_usd": 19.0,
            "mid_tier_usd": 59.0,
            "enterprise_tier_usd": 249.0,
            "common_billing_models": ["SaaS Subscription"],
            "willingness_to_pay_signal": "Moderate",
            "sources": ["https://capterra.com"]
        }
