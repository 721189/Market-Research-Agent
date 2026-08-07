import os
import sys

print("STEP 1: importing project modules...", flush=True)
from tools import web_search_tool  # noqa: E402
from tasks import FinancialAnalysis, create_tasks  # noqa: E402
from agents import build_agents, build_llm  # noqa: E402

print("STEP 2: modules imported", flush=True)
print("web_search_tool:", type(web_search_tool).__name__, flush=True)

print("STEP 3: building LLM + agents (reads .env)...", flush=True)
llm = build_llm()
print("llm model:", getattr(llm, "model", "?"), flush=True)
trend, fin, director = build_agents(llm)
print("agents:", trend.role, "|", fin.role, "|", director.role, flush=True)

print("STEP 4: creating tasks...", flush=True)
comp_task, fin_task, launch_task = create_tasks(
    "A collapsible silicone water bottle with filter",
    trend,
    fin,
    director,
)
print("tasks:", comp_task.name, "|", fin_task.name, "|", launch_task.name, flush=True)
print("fin task output_pydantic:", getattr(fin_task, "output_pydantic", None), flush=True)

print("STEP 5: testing parse_financials logic...", flush=True)
import json  # noqa: E402

from main import parse_financials  # noqa: E402

sample = {
    "product_name": "BottleX",
    "estimated_cogs": 4.5,
    "suggested_retail_price": 14.99,
    "projected_margin_percentage": 70.0,
    "key_competitor_prices": ["Competitor A: $12.99"],
}
parsed = parse_financials(sample)
print("parsed dict ->", parsed.model_dump() if parsed else None, flush=True)
parsed_json = parse_financials(json.dumps(sample))
print("parsed json ->", parsed_json.model_dump() if parsed_json else None, flush=True)
parsed_obj = parse_financials(FinancialAnalysis(**sample))
print("parsed obj ->", parsed_obj is not None, flush=True)

print("STEP 6: streamlit AppTest boot...", flush=True)
from streamlit.testing.v1 import AppTest  # noqa: E402

at = AppTest.from_file("main.py", default_timeout=120)
at.run(timeout=120)
print("app exceptions:", at.exception, flush=True)
print("title count:", len(at.title), "| text_areas:", len(at.text_area), flush=True)
print("buttons:", [b.label for b in at.button], flush=True)
print("sidebar markdown present:", len(at.sidebar) > 0, flush=True)

print("SMOKE TEST PASSED", flush=True)
