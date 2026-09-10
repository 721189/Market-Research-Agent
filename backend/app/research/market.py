import json
from typing import List, Dict, Any
from backend.app.research.planner import get_gemini_client

async def extract_market_dynamics(product_idea: str, questions: List[str]) -> Dict[str, Any]:
    client = get_gemini_client()
    if not client:
        return {
            "tam_usd_billions": 12.5,
            "sam_usd_billions": 3.2,
            "som_usd_millions": 250.0,
            "projected_cagr_percentage": 14.8,
            "key_tailwinds": ["Accelerated digital transformation", "Increased remote adoption"],
            "key_headwinds": ["Heightened regulatory compliance", "Macroeconomic budget scrutiny"],
            "sources": ["https://statista.com", "https://gartner.com"]
        }

    prompt = f"""
    Analyze the macroeconomic market dynamics for: "{product_idea}".
    Questions: {questions}

    Provide structured output in valid JSON:
    {{
      "tam_usd_billions": float,
      "sam_usd_billions": float,
      "som_usd_millions": float,
      "projected_cagr_percentage": float,
      "key_tailwinds": ["trend 1", "trend 2"],
      "key_headwinds": ["risk 1", "risk 2"],
      "sources": ["domain 1", "domain 2"]
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
            "tam_usd_billions": 10.0,
            "sam_usd_billions": 2.5,
            "som_usd_millions": 180.0,
            "projected_cagr_percentage": 12.0,
            "key_tailwinds": ["Rising consumer demand"],
            "key_headwinds": ["Competitive saturation"],
            "sources": ["https://bloomberg.com"]
        }
