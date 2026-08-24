"""Agent definitions for the market research crew.

Configures the LLM (OpenRouter primary, Groq fallback) through
CrewAI's LLM class. Uses the OpenAI compatibility layer workaround
via LiteLLM's ``openai/`` prefix to strip unsupported Anthropic-style
'cache_breakpoint' tags from messages.
"""

import litellm
from crewai import Agent, LLM
from dotenv import load_dotenv

from .routing import get_llm_config
from .tools import web_search_tool

load_dotenv()

# Force LiteLLM to aggressively drop unsupported parameters
litellm.drop_params = True


def build_llm(task_type: str = "deep") -> LLM:
    """Build a CrewAI LLM routed by task type (see ``routing.py``).

    Accepts routing keys (``scrape`` / ``financial`` / ``product``) or the
    legacy complexity keys (``quick`` / ``deep`` / ``batch``). Reads provider,
    model and base URL from :func:`routing.get_llm_config`.
    """
    cfg = get_llm_config(task_type)
    if not cfg.get("api_key"):
        raise RuntimeError(
            "An LLM API key is not set for the requested route. Add "
            "OPENROUTER_API_KEY (or GROQ_API_KEY as fallback, and "
            "DEEPINFRA_API_KEY for batch mode) to your .env "
            "file and restart the app."
        )
    return LLM(
        model=cfg["model"],
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        temperature=0.2,
    )


def build_agents(
    llm: LLM | None = None,
    complexity: str = "deep",
) -> tuple[Agent, Agent, Agent]:
    """Build the three agents with task-aware LLM routing.

    Args:
        llm: Optional shared ``LLM``. When provided all agents use it
            (backward compatible). When omitted, each agent receives a routed
            ``LLM`` from :func:`build_llm`.
        complexity: ``quick`` (all on 8B), ``deep`` (task-routed: scrape on
            8B, financial/product on 70B) or ``batch`` (DeepInfra for all,
            falling back to Groq deep when the key is unset).

    Returns:
        A tuple of ``(trend_scraper, financial_analyst, product_director)``.
    """
    if llm is not None:
        trend_llm = financial_llm = product_llm = llm
    elif complexity == "quick":
        trend_llm = financial_llm = product_llm = build_llm("quick")
    elif complexity == "batch":
        trend_llm = financial_llm = product_llm = build_llm("batch")
    else:
        trend_llm = build_llm("scrape")
        financial_llm = build_llm("financial")
        product_llm = build_llm("product")

    trend_scraper = Agent(
        role="Trend Scraper",
        goal=(
            "Uncover current market trends, competitor products, and pricing "
            "by searching the web, so the crew prices and positions the new "
            "product correctly."
        ),
        backstory=(
            "A tireless internet researcher who scans retailer sites, review "
            "forums, and industry blogs to map out who is selling what, for "
            "how much, and where customers are unhappy."
        ),
        tools=[web_search_tool],
        llm=trend_llm,
        verbose=True,
        allow_delegation=False,
        memory=False,
        max_iter=4,
    )

    financial_analyst = Agent(
        role="Financial Analyst",
        goal=(
            "Turn market data into a concrete, defensible pricing model: "
            "estimate COGS, pick a retail price, and calculate the gross "
            "margin percentage for the product."
        ),
        backstory=(
            "A numbers-first analyst with experience in unit economics for "
            "physical and digital products. You always back a recommendation "
            "with the competitor prices you found on the web."
        ),
        tools=[web_search_tool],
        llm=financial_llm,
        verbose=True,
        allow_delegation=False,
        memory=False,
        max_iter=4,
    )

    product_director = Agent(
        role="Product Director",
        goal=(
            "Synthesize the research and financial analysis into a crisp, "
            "actionable Markdown launch brief a product team can execute."
        ),
        backstory=(
            "A pragmatic product leader who has launched dozens of products. "
            "You write short, confident briefs: positioning, audience, "
            "pricing rationale, a 90-day plan, and honest risks."
        ),
        tools=[web_search_tool],
        llm=product_llm,
        verbose=True,
        allow_delegation=False,
        memory=False,
        max_iter=4,
    )

    return trend_scraper, financial_analyst, product_director