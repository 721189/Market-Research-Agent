"""Streamlit dashboard for the Multi-Agent Market Research platform.

Flow: user enters a product idea → the crew (Trend Scraper → Financial
Analyst → Product Director) runs async → the UI shows per-agent progress,
the financial metric cards, and the final Markdown launch brief.
"""

import asyncio
import json
import os

import streamlit as st
from crewai import Crew, Process
from dotenv import load_dotenv

from agents import build_agents, build_llm
from tasks import FinancialAnalysis, create_tasks

load_dotenv()

# --------------------------------------------------------------------------- #
# Task order (sequential crew) — used to drive progress states
# --------------------------------------------------------------------------- #
TASK_ORDER = ["Competitor Scrape", "Financial Margin", "Product Launch Brief"]

AGENT_EMOJI = {
    "Competitor Scrape": "🕵️",
    "Financial Margin": "🧮",
    "Product Launch Brief": "📄",
}


# --------------------------------------------------------------------------- #
# Cartoon-brutalist styling
# --------------------------------------------------------------------------- #
BRUTALIST_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap');

.stApp { background: #fff9e6; }
.stApp, .stApp * { font-family: 'Space Grotesk', sans-serif; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.5px; }

.block-container { padding-top: 2rem; padding-bottom: 3rem; }

/* Buttons */
.stButton > button {
    background: #ffd23f;
    border: 3px solid #1a1a1a;
    border-radius: 12px;
    box-shadow: 5px 5px 0 #1a1a1a;
    font-weight: 700;
    color: #1a1a1a;
    padding: 0.7rem 1.6rem;
}
.stButton > button:hover { transform: translate(-1px, -1px); box-shadow: 6px 6px 0 #1a1a1a; }
.stButton > button:active { transform: translate(2px, 2px); box-shadow: 2px 2px 0 #1a1a1a; }
.stButton > button:disabled { opacity: 0.5; transform: none; box-shadow: 5px 5px 0 #1a1a1a; }

/* Inputs */
.stTextArea textarea, .stTextInput input {
    border: 3px solid #1a1a1a !important;
    border-radius: 10px !important;
    box-shadow: 4px 4px 0 #1a1a1a;
    background: #ffffff;
}

/* Status boxes */
div[data-testid="stStatus"] {
    background: #ffffff;
    border: 3px solid #1a1a1a;
    border-radius: 12px;
    box-shadow: 4px 4px 0 #1a1a1a;
}

/* Bordered containers (launch brief) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 3px solid #1a1a1a !important;
    border-radius: 12px;
    box-shadow: 5px 5px 0 #1a1a1a;
    background: #ffffff;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #b3e0ff;
    border-right: 3px solid #1a1a1a;
}
[data-testid="stSidebar"] .stMarkdown { color: #1a1a1a; }

/* Custom metric cards */
.metric-card {
    background: #ffffff;
    border: 3px solid #1a1a1a;
    border-radius: 12px;
    box-shadow: 6px 6px 0 #1a1a1a;
    padding: 16px 18px;
    margin-bottom: 12px;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.metric-card .card-title { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #55524a; margin-bottom: 6px; }
.metric-card .card-value { font-size: 1.7rem; font-weight: 700; line-height: 1.1; }
.metric-card .card-sub { margin-top: 6px; font-size: 0.8rem; color: #55524a; }

/* Key badges in the sidebar */
.key-badge-ok, .key-badge-missing { display: inline-block; padding: 3px 10px; border: 2px solid #1a1a1a; border-radius: 999px; font-size: 0.75rem; font-weight: 700; margin-bottom: 6px; }
.key-badge-ok { background: #9ef01a; }
.key-badge-missing { background: #ff5d5d; color: #1a1a1a; }
"""


def inject_css() -> None:
    """Send the brutalist stylesheet to the app."""
    st.markdown(f"<style>{BRUTALIST_CSS}</style>", unsafe_allow_html=True)


def render_hero() -> None:
    """Render the chunky hero header."""
    st.markdown(
        """
        <div style="border:4px solid #1a1a1a;border-radius:16px;background:#ffffff;
                    box-shadow:8px 8px 0 #1a1a1a;padding:22px 26px;margin-bottom:28px;">
          <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
            <div style="font-size:2.6rem;line-height:1;">🕵️</div>
            <div>
              <div style="font-size:2rem;font-weight:700;line-height:1.05;">Market&nbsp;Research&nbsp;Crew</div>
              <div style="font-size:0.95rem;color:#55524a;margin-top:4px;">
                Competitor scoop → Margin math → Launch brief · CrewAI + Groq + Tavily
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Sidebar with API-key status and instructions."""
    with st.sidebar:
        st.markdown("## 🧰 Setup")
        tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
        groq_ok = bool(os.getenv("GROQ_API_KEY"))

        if tavily_ok:
            st.markdown(
                '<span class="key-badge-ok">✓ TAVILY_API_KEY set</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="key-badge-missing">✗ TAVILY_API_KEY missing</span>',
                unsafe_allow_html=True,
            )
        if groq_ok:
            st.markdown(
                '<span class="key-badge-ok">✓ GROQ_API_KEY set</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<span class="key-badge-missing">✗ GROQ_API_KEY missing</span>',
                unsafe_allow_html=True,
            )

        if not (tavily_ok and groq_ok):
            st.warning("Add the missing keys to your `.env` file and restart the app.")
        else:
            st.success("All keys present. Ready to research!")

        st.markdown("---")
        st.markdown(
            """
            **How it works**

            1. **Trend Scraper** searches the web for competitors & pricing.
            2. **Financial Analyst** estimates COGS, price & margin.
            3. **Product Director** writes the launch brief.
            """
        )


# --------------------------------------------------------------------------- #
# Core research execution
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def get_llm():
    """Build and cache the Groq-backed CrewAI LLM (raises if key missing)."""
    return build_llm()


def make_task_callback(statuses: dict[str, st.status]):
    """Return a CrewAI ``task_callback`` that drives the status widgets.

    Sequential crew: when a task completes, mark it done and start the next.
    """

    def _on_task_end(task) -> None:
        try:
            name = getattr(task, "name", None)
            if not name or name not in statuses:
                return
            statuses[name].update(
                label=f"{AGENT_EMOJI[name]} {name} — complete", state="complete"
            )
            idx = TASK_ORDER.index(name)
            if idx + 1 < len(TASK_ORDER):
                nxt = TASK_ORDER[idx + 1]
                statuses[nxt].update(
                    label=f"{AGENT_EMOJI[nxt]} {nxt} — running",
                    state="running",
                )
        except Exception:
            # Progress callbacks must never break the crew run.
            pass

    return _on_task_end


async def run_crew(product_idea: str, llm, task_callback):
    """Execute the three-agent crew sequentially and return the crew result."""
    trend_scraper, financial_analyst, product_director = build_agents(llm)
    competitor_task, financial_task, launch_task = create_tasks(
        product_idea, trend_scraper, financial_analyst, product_director
    )

    crew = Crew(
        agents=[trend_scraper, financial_analyst, product_director],
        tasks=[competitor_task, financial_task, launch_task],
        process=Process.sequential,
        verbose=True,
        task_callback=task_callback,
    )
    return await crew.kickoff_async(inputs={})


def parse_financials(data) -> FinancialAnalysis | None:
    """Coerce the financial task output into a FinancialAnalysis instance."""
    if isinstance(data, FinancialAnalysis):
        return data
    if isinstance(data, dict):
        try:
            return FinancialAnalysis(**data)
        except Exception:
            return None
    if isinstance(data, str):
        try:
            return FinancialAnalysis(**json.loads(data))
        except Exception:
            return None
    return None


def render_financial_cards(fin: FinancialAnalysis) -> None:
    """Render the four metric cards + competitor price list."""
    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(
        f"""<div class="metric-card">
            <div class="card-title">Estimated COGS</div>
            <div class="card-value">${fin.estimated_cogs:,.2f}</div>
            <div class="card-sub">per unit (USD)</div>
        </div>""",
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"""<div class="metric-card">
            <div class="card-title">Suggested Retail</div>
            <div class="card-value">${fin.suggested_retail_price:,.2f}</div>
            <div class="card-sub">per unit (USD)</div>
        </div>""",
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"""<div class="metric-card">
            <div class="card-title">Projected Margin</div>
            <div class="card-value">{fin.projected_margin_percentage:,.1f}%</div>
            <div class="card-sub">gross margin</div>
        </div>""",
        unsafe_allow_html=True,
    )
    c4.markdown(
        f"""<div class="metric-card">
            <div class="card-title">Competitors Tracked</div>
            <div class="card-value">{len(fin.key_competitor_prices)}</div>
            <div class="card-sub">priced on the web</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("#### 💰 Competitor price check")
    for price in fin.key_competitor_prices:
        st.markdown(f"- {price}")


# --------------------------------------------------------------------------- #
# Main app
# --------------------------------------------------------------------------- #
def run_research(product_idea: str) -> None:
    """Kick off the async crew and render results."""
    llm = get_llm()

    statuses: dict[str, st.status] = {}
    for task_name in TASK_ORDER:
        statuses[task_name] = st.status(
            label=f"{AGENT_EMOJI[task_name]} {task_name} — queued",
            expanded=(task_name == TASK_ORDER[0]),
        )
    statuses[TASK_ORDER[0]].update(
        label=f"{AGENT_EMOJI[TASK_ORDER[0]]} {TASK_ORDER[0]} — running",
        state="running",
    )

    try:
        result = asyncio.run(
            run_crew(product_idea, llm, make_task_callback(statuses))
        )
    except Exception as exc:
        for status in statuses.values():
            status.update(state="error")
        st.error(f"❌ Research failed: {exc}")
        return

    for status in statuses.values():
        status.update(state="complete")

    # --- Extract outputs --------------------------------------------------- #
    tasks_output = getattr(result, "tasks_output", []) or []
    financial_data = tasks_output[1].raw if len(tasks_output) > 1 else None
    launch_output = tasks_output[2] if len(tasks_output) > 2 else None

    fin = parse_financials(financial_data)

    # --- Render financial dashboard ---------------------------------------- #
    st.markdown("## 🧮 Financial Analysis")
    if fin is not None:
        render_financial_cards(fin)
    else:
        st.warning("No structured financial data was returned. Showing raw output:")
        if financial_data is not None:
            st.code(str(financial_data), language="json")

    # --- Render launch brief ------------------------------------------------ #
    st.markdown("## 📄 Product Launch Brief")
    if launch_output is not None:
        brief_md = (
            getattr(launch_output, "raw", None)
            or getattr(launch_output, "output", None)
            or getattr(launch_output, "summary", None)
            or ""
        )
        if brief_md:
            with st.container(border=True):
                st.markdown(brief_md)
        else:
            st.info("No brief text returned.")
    else:
        st.info("No launch brief output available.")
        st.download_button(
            "⬇️ Download raw crew result",
            data=str(result),
            file_name="crew_result.txt",
            mime="text/plain",
        )


def main() -> None:
    st.set_page_config(
        page_title="Market Research Crew",
        page_icon="🕵️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    render_hero()
    render_sidebar()

    st.markdown("## 💡 What are you launching?")
    product_idea = st.text_area(
        "Describe your product idea",
        placeholder=(
            "e.g. A collapsible, dishwasher-safe silicone water bottle "
            "with a built-in filter, aimed at hikers."
        ),
        height=110,
    )

    ready = bool(os.getenv("TAVILY_API_KEY")) and bool(os.getenv("GROQ_API_KEY"))
    run_clicked = st.button("🚀 Run the Crew", type="primary", disabled=not ready)

    if run_clicked:
        if not product_idea.strip():
            st.error("Please describe your product idea first.")
            return
        st.markdown("---")
        st.markdown("## 🔄 Research in progress")
        run_research(product_idea.strip())


if __name__ == "__main__":
    main()
