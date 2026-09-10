import json
from typing import List, Dict, Any
from backend.app.research.planner import get_gemini_client

async def extract_competitors(product_idea: str, questions: List[str]) -> List[Dict[str, Any]]:
    client = get_gemini_client()
    if not client:
        return [
            {
                "name": "Market Incumbent",
                "features": ["Standard feature set", "Global distribution"],
                "positioning": "Established Enterprise",
                "pricing": "$49.99/mo",
                "weaknesses": ["Slow innovation", "High legacy support cost"],
                "sources": ["https://techcrunch.com", "https://forbes.com"]
            },
            {
                "name": "Agile Disruptor",
                "features": ["Modern UI", "API-first architecture"],
                "positioning": "High-growth SMB",
                "pricing": "$19.99/mo",
                "weaknesses": ["Limited enterprise compliance", "Smaller support team"],
                "sources": ["https://producthunt.com"]
            }
        ]

    prompt = f"""
    Perform deep competitor intelligence on: "{product_idea}".
    Answer these targeted questions: {questions}

    Extract at least 3-5 real or benchmark competitors.
    For each competitor, provide:
    - name: company or product name
    - features: list of 3 key product features
    - positioning: market positioning (e.g., Luxury, Enterprise, Budget, D2C)
    - pricing: exact or estimated pricing structure
    - weaknesses: customer complaints or technical limitations
    - sources: list of public domains or URLs where data was sourced

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
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception:
        return [
            {
                "name": "Direct Competitor Alpha",
                "features": ["Core feature workflow", "Mobile app"],
                "positioning": "Mid-Market",
                "pricing": "$29/mo",
                "weaknesses": ["Steep learning curve"],
                "sources": ["https://news.ycombinator.com"]
            }
        ]
