#!/usr/bin/env python
"""CrewAI AMP flow entry point.

Defines a ``MarketResearchAgentFlow(Flow[AppState])`` subclass (required by
CrewAI AMP validation) that runs the headless research pipeline, and exposes
the ``kickoff`` / ``run_with_trigger`` console scripts referenced by
``[project.scripts]`` in ``pyproject.toml``.
"""

import asyncio
import json
import os
import sys

from crewai.flow import Flow, start

from .flow import auto_research_async
from .state import AppState


class MarketResearchAgentFlow(Flow[AppState]):
    """AMP flow wrapper around the market research pipeline."""

    @start()
    async def research(self, crewai_trigger_payload: dict | None = None):
        if crewai_trigger_payload:
            product = crewai_trigger_payload.get("product_idea") or os.getenv(
                "PRODUCT_IDEA", "Smart Water Bottle"
            )
            mode = crewai_trigger_payload.get("mode") or os.getenv(
                "ANALYSIS_MODE", "deep"
            )
        else:
            product = os.getenv("PRODUCT_IDEA", "Smart Water Bottle")
            mode = os.getenv("ANALYSIS_MODE", "deep")

        payload, _flow = await auto_research_async(product, mode=mode)
        return payload


def _run_async(flow: MarketResearchAgentFlow) -> dict:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(flow.kickoff_async())
    finally:
        loop.close()


def kickoff() -> None:
    """Run the flow headlessly and print the JSON result."""
    result = _run_async(MarketResearchAgentFlow())
    print(json.dumps(result, default=str, indent=2))


def run_with_trigger() -> None:
    """Run the flow using a JSON trigger payload supplied as ``argv[1]``."""
    if len(sys.argv) < 2:
        raise Exception(
            "No trigger payload provided. Pass a JSON payload as an argument."
        )
    trigger_payload = json.loads(sys.argv[1])
    flow = MarketResearchAgentFlow()
    result = _run_async(flow)
    print(json.dumps(result, default=str, indent=2))


if __name__ == "__main__":
    kickoff()