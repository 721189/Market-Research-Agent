"""Task definitions for the market research crew.

Defines the ``FinancialAnalysis`` Pydantic schema and three CrewAI tasks:

1. ``Competitor Scrape`` — gathers competitor/pricing data from the web.
2. ``Financial Margin`` — structured (Pydantic) cost/price/margin analysis.
3. ``Product Launch Brief`` — the final markdown go-to-market brief.

The agents are injected by the caller (``main.py``) so this module has no
dependency on ``agents.py`` and there is no circular import.
"""

from pydantic import BaseModel
from crewai import Agent, Task

from schemas import ConfidenceScore
from tools import web_search_tool


def validate_input(product_idea: str) -> bool:
    """Guardrail: reject empty or too-short product ideas before tasks run.

    Args:
        product_idea: The user's product idea text.

    Returns:
        Always ``True`` when validation passes.

    Raises:
        ValueError: If the input has fewer than 3 non-whitespace characters.
    """
    if len(product_idea.strip()) < 3:
        raise ValueError("Product idea must be at least 3 characters")
    return True


class FinancialAnalysis(BaseModel):
    """Structured financial view of a product idea.

    Attributes:
        product_name: The product being analysed.
        estimated_cogs: Estimated cost of goods sold per unit in USD.
        suggested_retail_price: Recommended retail price per unit in USD.
        projected_margin_percentage: Gross margin percentage implied by the
            price and COGS.
        key_competitor_prices: Prices of comparable competitor products,
            e.g. "Competitor A: $9.99".
    """

    product_name: str
    estimated_cogs: float
    suggested_retail_price: float
    projected_margin_percentage: float
    key_competitor_prices: list[str]


def create_tasks(
    product_idea: str,
    trend_scraper: Agent,
    financial_analyst: Agent,
    product_director: Agent,
) -> tuple[Task, Task, Task, Task]:
    """Build the three research tasks wired together with ``context``.

    Args:
        product_idea: The user's product idea text.
        trend_scraper: Agent 1 — Trend Scraper.
        financial_analyst: Agent 2 — Financial Analyst.
        product_director: Agent 3 — Product Director.

    Returns:
        A tuple of ``(competitor_task, financial_task, launch_task)``.
    """
    validate_input(product_idea)
    competitor_task = Task(
        name="Competitor Scrape",
        description=(
            f"Research the market for this product idea: \"{product_idea}\".\n\n"
            "**CRITICAL TOKEN LIMIT INSTRUCTION:**\n"
            "Your output MUST be under 3,000 characters total.\n"
            "Limit your research to the TOP 5 most relevant competitors ONLY.\n\n"
            "Using the provided Web Search tool, find:\n"
            "- The top 5 main competitors and what comparable products they sell.\n"
            "- Current market prices of those specific products (numeric values where possible).\n"
            "- A brief (1-sentence) summary of each competitor's positioning.\n\n"
            "**Format your output as:**\n"
            "Competitor 1: Name — Product — Price — Positioning\n"
            "Competitor 2: Name — Product — Price — Positioning\n"
            "... (repeat for top 5)\n\n"
            "DO NOT include raw search results, long paragraphs, or analysis. Be concise."
        ),
        expected_output=(
            "A bulleted list of exactly 5 competitors with product, price, and positioning. "
            "Total output under 3,000 characters."
        ),
        agent=trend_scraper,
        tools=[web_search_tool],
    )

    financial_task = Task(
        name="Financial Margin",
        description=(
            "Using the competitor research report (see context) and your own "
            "web research on this product: "
            f'"{product_idea}",\n'
            "- Estimate the cost of goods sold (COGS) per unit in USD.\n"
            "- Recommend a retail price that stays competitive.\n"
            "- Compute the projected gross margin percentage.\n"
            "- List current prices of 3-5 key competitors.\n"
            "Be explicit and numeric — no vague ranges without a recommended value."
        ),
        expected_output=(
            "A complete FinancialAnalysis object: product_name, estimated_cogs, "
            "suggested_retail_price, projected_margin_percentage, and "
            "key_competitor_prices (3-5 items, each a quoted string)."
        ),
        agent=financial_analyst,
        output_pydantic=FinancialAnalysis,
        context=[competitor_task],
    )

    launch_task = Task(
        name="Product Launch Brief",
        description=(
            "You are the Product Director. Produce a go-to-market launch brief "
            f'for the product: "{product_idea}".\n\n'
            "Use the financial analysis from the context to ground every claim.\n"
            "The brief MUST include the following Markdown sections:\n"
            "## Executive Summary\n"
            "## Target Audience\n"
            "## Competitive Positioning\n"
            "## Pricing Strategy & Margin\n"
            "## Launch Plan (90 days)\n"
            "## Risks & Mitigations"
        ),
        expected_output=(
            "A polished Markdown product launch brief with the six required "
            "sections, grounded in the financial data and competitor prices."
        ),
        agent=product_director,
        context=[financial_task],
    )

    confidence_task = Task(
        name="Confidence Scoring",
        description=(
            "Review the financial analysis and the product launch brief for "
            f'the product: "{product_idea}".\n\n'
            "Evaluate the confidence of the insights generated, scoring them out of 100 based on:\n"
            "- Source reliability\n"
            "- Evidence coverage\n"
            "- Consistency across data points\n"
            "- Your own self-assessment as an LLM\n\n"
            "Identify specific low-confidence and high-confidence insights with reasons."
        ),
        expected_output=(
            "A structured JSON response matching the ConfidenceScore schema."
        ),
        agent=product_director,
        output_pydantic=ConfidenceScore,
        context=[financial_task, launch_task],
    )

    return (competitor_task, financial_task, launch_task, confidence_task)
