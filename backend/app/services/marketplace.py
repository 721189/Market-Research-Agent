import uuid
import datetime
from typing import List, Dict, Any, Optional

DEFAULT_TEMPLATES = [
    {
        "id": "template_saas_pricing",
        "title": "B2B SaaS Pricing & Packaging Teardown",
        "description": "Analyze competitor tiering, seat vs consumption metric models, and calculate target gross margins.",
        "category": "saas",
        "mode": "deep",
        "prompt_template": "Perform a rigorous pricing audit and unit economics analysis for: {product_idea}. Extract competitor tier structures, pricing metric anchors, and contribution margins."
    },
    {
        "id": "template_competitor_matrix",
        "title": "Comprehensive Competitor & Threat Matrix",
        "description": "Exhaustive competitor mapping across direct incumbents, open-source challengers, and regional entrants.",
        "category": "market_strategy",
        "mode": "deep",
        "prompt_template": "Identify all primary and secondary market competitors for {product_idea}. Synthesize SWOT comparison, differentiation vectors, and defensibility moats."
    },
    {
        "id": "template_quick_tam_cagr",
        "title": "Rapid TAM, SAM & Growth Rate Flash Brief",
        "description": "30-second rapid estimation of Total Addressable Market with empirical citation verification.",
        "category": "market_sizing",
        "mode": "quick",
        "prompt_template": "Calculate Total Addressable Market (TAM), Serviceable Addressable Market (SAM), and CAGR growth forecasts for {product_idea}."
    },
    {
        "id": "template_d2c_unit_economics",
        "title": "D2C Physical Product Unit Economics",
        "description": "Model manufacturing COGS, freight, packaging, return rates, and break-even unit volumes.",
        "category": "d2c",
        "mode": "deep",
        "prompt_template": "Evaluate physical product unit economics, landed COGS, wholesale margins, and break-even inventory turns for: {product_idea}."
    }
]

class MarketplaceService:
    @staticmethod
    def list_templates() -> List[Dict[str, Any]]:
        return DEFAULT_TEMPLATES

    @staticmethod
    def get_template(template_id: str) -> Optional[Dict[str, Any]]:
        for t in DEFAULT_TEMPLATES:
            if t["id"] == template_id:
                return t
        return None

marketplace_service = MarketplaceService()
