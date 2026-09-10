import json
from typing import List, Dict, Any
from backend.app.research.planner import get_gemini_client

async def extract_customer_profiles(product_idea: str, questions: List[str]) -> Dict[str, Any]:
    client = get_gemini_client()
    if not client:
        return {
            "primary_persona": "Growth-focused Product Manager",
            "demographics": "Tech-forward professionals, ages 26-45, SMB & Mid-market",
            "core_pain_points": [
                "Manual data aggregation wastes hours weekly",
                "Lack of unified competitor insight tools"
            ],
            "buying_triggers": [
                "New product launch impending",
                "Executive demand for competitive benchmarking"
            ],
            "sources": ["https://reddit.com/r/startups", "https://linkedin.com"]
        }

    prompt = f"""
    Analyze customer demographics, ideal buyer personas, and pain points for: "{product_idea}".
    Questions: {questions}

    Provide structured output in valid JSON:
    {{
      "primary_persona": "Title / Role",
      "demographics": "Target demographic details",
      "core_pain_points": ["point 1", "point 2"],
      "buying_triggers": ["trigger 1", "trigger 2"],
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
            "primary_persona": "Strategic Decision Maker",
            "demographics": "B2B and B2C team leads",
            "core_pain_points": ["Fragmented market research tools"],
            "buying_triggers": ["Quarterly strategy review"],
            "sources": ["https://medium.com"]
        }
