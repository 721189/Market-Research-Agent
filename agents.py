"""Agent definitions for the market research crew.

Configures the Groq LLM through CrewAI's LLM class.
Uses the OpenAI compatibility layer workaround to force LiteLLM to 
strip unsupported Anthropic-style 'cache_breakpoint' tags from messages.
"""

import os
import litellm
from crewai import Agent, LLM
from dotenv import load_dotenv

from tools import web_search_tool

load_dotenv()

# Force LiteLLM to aggressively drop unsupported parameters
litellm.drop_params = True


def build_llm(mode: str = "deep") -> LLM:
    """Build Groq LLM. mode='quick' -> 8B, mode='deep' -> 70B."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(GROQ_API_KEY=your_key_here) and restart the app."
        )

    model = (
        "openai/llama-3.1-8b-instant"
        if mode == "quick"
        else "openai/llama-3.3-70b-versatile"
    )
    return LLM(
        model=model,
        api_key=groq_api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.7,
    )


def build_agents(llm: LLM) -> tuple[Agent, Agent, Agent]:
    """Build the three agents sharing a single Groq LLM and the web search tool.

    Args:
        llm: The CrewAI ``LLM`` instance created by :func:`build_llm`.

    Returns:
        A tuple of ``(trend_scraper, financial_analyst, product_director)``.
    """
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
        llm=llm,
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
        llm=llm,
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
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=False,
        max_iter=4,
    )

    return trend_scraper, financial_analyst, product_director