from typing import Dict, Any

class CostService:
    """
    Central cost-control service tracking LLM tokens, search calls, and computing deterministic costs.
    """
    # Pricing table per 1M tokens in USD
    MODEL_PRICING: Dict[str, Dict[str, float]] = {
        "gemini-1.5-flash": {
            "input_per_million": 0.075,
            "output_per_million": 0.30,
        },
        "gemini-1.5-pro": {
            "input_per_million": 3.50,
            "output_per_million": 10.50,
        },
        "gemini-2.0-flash": {
            "input_per_million": 0.10,
            "output_per_million": 0.40,
        },
    }
    
    SEARCH_CALL_COST = 0.005 # $0.005 per web search API call

    @classmethod
    def calculate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
        search_calls: int = 0
    ) -> float:
        pricing = cls.MODEL_PRICING.get(model, cls.MODEL_PRICING["gemini-1.5-flash"])
        input_cost = (input_tokens / 1_000_000) * pricing["input_per_million"]
        output_cost = (output_tokens / 1_000_000) * pricing["output_per_million"]
        search_cost = search_calls * cls.SEARCH_CALL_COST
        
        total = round(input_cost + output_cost + search_cost, 6)
        return total

cost_service = CostService()
