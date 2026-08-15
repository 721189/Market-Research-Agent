"""Custom CrewAI tools for the market research crew.

Uses Tavily's search API wrapped as a CrewAI BaseTool via the
``crewai.tools.tool`` decorator so agents can call it during execution.
"""

import json
import os
from typing import Annotated

from crewai.tools import tool
from dotenv import load_dotenv
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()


def _build_client() -> TavilyClient:
    """Construct the TavilyClient, enforcing that ``TAVILY_API_KEY`` is set.

    Raises:
        RuntimeError: If ``TAVILY_API_KEY`` is missing from the environment.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set. Add it to your .env file "
            "(TAVILY_API_KEY=your_key_here) and restart the app."
        )
    return TavilyClient(api_key=api_key)


@tool("Web Search")
def web_search_tool(question: Annotated[str, "The question to research on the web."]) -> str:
    """Search the web for real-time market, competitor, pricing, and trend data.

    Returns a JSON string with the top search results (title, url, and snippet)
    for the supplied question.
    """
    client = _build_client()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _search():
        return client.search(
            query=question,
            search_depth="advanced",
            max_results=6,
            include_answer=True,
        )

    response = _search()
    results = response.get("results", [])
    return json.dumps(
        {
            "question": question,
            "answer": response.get("answer"),
            "results": [
                {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
                for r in results
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
