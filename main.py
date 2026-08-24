"""Streamlit dashboard — Flow-driven market research with HITL + PDF."""

import asyncio
import json
import os

import streamlit as st
from crewai.flow.async_feedback.types import HumanFeedbackPending
from dotenv import load_dotenv

from agents import build_llm
from cache import get_cached, set_cached
from flow import kickoff_research, resume_research
from pdf_export import generate_pdf
from schemas import ConfidenceScore
from tasks import FinancialAnalysis

load_dotenv()

TASK_ORDER = [
    "Competitor Scrape",
    "Financial Margin",
    "Product Launch Brief",
    "Confidence Scoring",
]
AGENT_EMOJI = {
    "Competitor Scrape": "🕵️",
    "Financial Margin": "🧮",
    "Product Launch Brief": "📄",
    "Confidence Scoring": "🎯",
}

BRUTALIST_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap');
.stApp { background: #fff9e6; }
.stApp, .stApp * { font-family: 'Space Grotesk', sans-serif; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.5px; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; }
.stButton > button {
    background: #ffd23f; border: 3px solid #1a1a1a; border-radius: 12px;
    box-shadow: 5px 5px 0 #1a1a1a; font-weight: 700; color: #1a1a1a;
}
.metric-card {
    background: #fff; border: 3px solid #1a1a1a; border-radius: 12px;
    box-shadow: 6px 6px 0 #1a1a1a; padding: 16px; min-height: 110px;
}
.metric-card .card-title { font-size: 0.85rem; font-weight: 700; color: #555; }
.metric-card .card-value { font-size: 1.6rem; font-weight: 700; }
.confidence-bar { height: 12px; border-radius: 6px; background: #ecf0f1; margin: 4px 0 12px; }
.confidence-fill { height: 12px; border-radius: 6px; }
.key-badge-ok, .key-badge-missing { display: inline-block; padding: 3px 10px;
    border: 2px solid #1a1a1a; border-radius: 999px; font-size: 0.75rem; font-weight: 700; }
.key-badge-ok { background: #9ef01a; }
.key-badge-missing { background: #ff5d5d; }
"""


def init_session():
    defaults = {
        "stage": "idle",
        "pending_flow": None,
        "results": None,
        "product_idea": "",
        "editing": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def parse_financials(data) -> FinancialAnalysis | None:
    if isinstance(data, FinancialAnalysis):
        return data
    if isinstance(data, dict) and "estimated_cogs" in data:
        try:
            return FinancialAnalysis(**data)
        except Exception:
            pass
    if isinstance(data, str):
        try:
            return FinancialAnalysis(**json.loads(data))
        except Exception:
            pass
    return None


def parse_confidence(data) -> ConfidenceScore | None:
    if isinstance(data, ConfidenceScore):
        return data
    if isinstance(data, dict) and "overall_score" in data:
        try:
            return ConfidenceScore(**data)
        except Exception:
            pass
    return None


def render_financial_cards(fin: FinancialAnalysis):
    c1, c2, c3, c4 = st.columns(4)
    for col, title, val, sub in [
        (c1, "COGS", f"${fin.estimated_cogs:,.2f}", "per unit"),
        (c2, "Retail", f"${fin.suggested_retail_price:,.2f}", "per unit"),
        (c3, "Margin", f"{fin.projected_margin_percentage:.1f}%", "gross"),
        (c4, "Competitors", str(len(fin.key_competitor_prices)), "tracked"),
    ]:
        col.markdown(
            f'<div class="metric-card"><div class="card-title">{title}</div>'
            f'<div class="card-value">{val}</div><div>{sub}</div></div>',
            unsafe_allow_html=True,
        )
    for p in fin.key_competitor_prices:
        st.markdown(f"- {p}")


def render_confidence(conf: ConfidenceScore):
    color = "#2ecc71" if conf.overall_score >= 75 else "#f39c12" if conf.overall_score >= 50 else "#e74c3c"
    st.markdown(f"## 🎯 Confidence: **{conf.overall_score}/100**")
    for label, val in [
        ("Source Reliability", conf.source_reliability),
        ("Evidence Coverage", conf.evidence_coverage),
        ("Consistency", conf.consistency),
    ]:
        st.markdown(f"**{label}** — {val}/100")
        st.markdown(
            f'<div class="confidence-bar"><div class="confidence-fill" '
            f'style="width:{val}%;background:{color};"></div></div>',
            unsafe_allow_html=True,
        )
    if conf.high_confidence_insights:
        st.success("High confidence: " + "; ".join(conf.high_confidence_insights[:3]))
    if conf.low_confidence_insights:
        st.warning("Low confidence: " + "; ".join(conf.low_confidence_insights[:3]))
    if conf.summary:
        st.info(conf.summary)


def make_task_callback(statuses):
    def _on_task_end(task):
        try:
            name = getattr(task, "name", None)
            if name and name in statuses:
                statuses[name].update(label=f"{AGENT_EMOJI[name]} {name} — done", state="complete")
                idx = TASK_ORDER.index(name)
                if idx + 1 < len(TASK_ORDER):
                    nxt = TASK_ORDER[idx + 1]
                    statuses[nxt].update(label=f"{AGENT_EMOJI[nxt]} {nxt} — running", state="running")
        except Exception:
            pass
    return _on_task_end


def render_results(results: dict):
    fin = parse_financials(results.get("financials"))
    conf = parse_confidence(results.get("confidence"))
    brief = results.get("launch_brief", "")

    st.markdown("## 🧮 Financial Analysis")
    if fin:
        render_financial_cards(fin)
    else:
        st.warning("No structured financials.")

    if conf:
        render_confidence(conf)

    st.markdown("## 📄 Launch Brief")
    if brief:
        with st.container(border=True):
            st.markdown(brief)

    product = fin.product_name if fin else results.get("product_idea", "Product")
    summary = conf.summary if conf else (brief[:500] if brief else "Market research report.")
    if fin or brief:
        pdf_bytes = generate_pdf(product, summary, fin, conf, brief)
        st.download_button(
            "⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=f"{product.replace(' ', '_')}_report.pdf",
            mime="application/pdf",
        )


def run_flow(product_idea: str, mode: str):
    cached = get_cached(product_idea)
    if cached:
        st.success("⚡ Cache hit — instant result")
        st.session_state.results = cached
        st.session_state.stage = "complete"
        render_results(cached)
        return

    statuses = {
        n: st.status(f"{AGENT_EMOJI[n]} {n} — queued", expanded=(n == TASK_ORDER[0]))
        for n in TASK_ORDER
    }
    statuses[TASK_ORDER[0]].update(label=f"{AGENT_EMOJI[TASK_ORDER[0]]} {TASK_ORDER[0]} — running", state="running")

    try:
        result, flow = asyncio.run(
            kickoff_research(product_idea, mode, st.session_state, make_task_callback(statuses))
        )
    except Exception as exc:
        st.error(f"Research failed: {exc}")
        return

    if isinstance(result, HumanFeedbackPending) or st.session_state.get("stage") == "awaiting_review":
        # HITL gate reached. Persist the paused flow in session state and
        # rerun: the review UI (Approve / Edit / Reject) is rendered by main()
        # below on *every* rerun so its buttons stay clickable. Rendering those
        # buttons right here only ran on the "Run Research" click, which is why
        # clicking them appeared to do nothing.
        st.session_state.pending_flow = flow
        st.session_state.product_idea = product_idea
        st.session_state.mode = mode
        st.session_state.editing = False
        st.rerun()
        return

    _finalize(flow, product_idea)


def _resume(feedback: str, product_idea: str, mode: str, statuses):
    flow = st.session_state.pending_flow
    if not flow:
        st.error("No pending flow.")
        return False
    try:
        asyncio.run(resume_research(flow, feedback))
    except Exception as exc:
        st.error(f"Resume failed: {exc}")
        return False
    _finalize(flow, product_idea)
    return True


def render_review_ui():
    """Render the HITL review screen with working Approve / Edit / Reject buttons."""
    flow = st.session_state.pending_flow
    if not flow:
        st.error("No pending flow. Re-run research.")
        return
    product_idea = st.session_state.get("product_idea", "")
    fin = parse_financials(flow.state.financials)
    st.markdown("## ⏸️ Review Required")
    if fin:
        st.markdown("### Current financial analysis")
        render_financial_cards(fin)

    # --- Edit & Approve form (shown only after clicking Edit & Approve) ---
    if st.session_state.get("editing") and fin:
        st.markdown("### ✏️ Edit financials before approving")
        with st.form("edit_financials_form"):
            cogs = st.number_input("Estimated COGS ($)", value=float(fin.estimated_cogs), step=0.01)
            retail = st.number_input("Suggested retail price ($)", value=float(fin.suggested_retail_price), step=0.01)
            margin = st.number_input("Projected margin (%)", value=float(fin.projected_margin_percentage), step=0.1)
            comp_prices = st.text_area(
                "Competitor prices (one per line)", value="\n".join(fin.key_competitor_prices)
            )
            submitted = st.form_submit_button("💾 Save & Approve", type="primary")
        if submitted:
            # Apply edits to the pending flow state, then resume as approved.
            flow.state.financials = {
                "product_name": fin.product_name,
                "estimated_cogs": cogs,
                "suggested_retail_price": retail,
                "projected_margin_percentage": margin,
                "key_competitor_prices": [ln.strip() for ln in comp_prices.splitlines() if ln.strip()],
            }
            if _resume("approved", product_idea, "", None):
                st.rerun()
            return
        if st.button("↩️ Cancel editing"):
            st.session_state.editing = False
            st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Approve", type="primary"):
            if _resume("approved", product_idea, "", None):
                st.rerun()
        if c2.button("✏️ Edit & Approve"):
            st.session_state.editing = True
            st.rerun()
        if c3.button("❌ Reject"):
            st.session_state.stage = "idle"
            st.session_state.pending_flow = None
            st.session_state.editing = False
            st.warning("Research rejected. You can run a new query.")


def _finalize(flow, product_idea: str = ""):
    results = {
        "product_idea": product_idea,
        "financials": flow.state.financials,
        "launch_brief": flow.state.launch_brief,
        "confidence": flow.state.confidence,
    }
    st.session_state.results = results
    st.session_state.stage = "complete"
    st.session_state.pending_flow = None
    st.session_state.editing = False
    set_cached(product_idea, results)
    for n in TASK_ORDER:
        pass  # statuses may be out of scope
    return results


def main():
    st.set_page_config(page_title="Market Research Crew", page_icon="🕵️", layout="wide")
    st.markdown(f"<style>{BRUTALIST_CSS}</style>", unsafe_allow_html=True)
    init_session()

    with st.sidebar:
        st.markdown("## 🧰 Setup")
        for key, label in [("TAVILY_API_KEY", "Tavily"), ("OPENROUTER_API_KEY", "OpenRouter"), ("GROQ_API_KEY", "Groq"), ("DEEPINFRA_API_KEY", "DeepInfra")]:
            ok = bool(os.getenv(key))
            cls = "key-badge-ok" if ok else "key-badge-missing"
            st.markdown(f'<span class="{cls}">{"✓" if ok else "✗"} {label}</span>', unsafe_allow_html=True)
        mode = st.radio("Analysis depth", ["quick", "deep"], format_func=lambda x: "Quick Look (8B)" if x == "quick" else "Deep Analysis (70B)")
        batch_mode = st.checkbox("Use Batch API (~20% cheaper, slower)")
        if batch_mode:
            mode = "batch"

    st.markdown("# 🕵️ Market Research Crew")
    st.caption("Competitor scrape → Financials → HITL review → Launch brief + Confidence score")

    product_idea = st.text_area("Product idea", height=100)
    ready = bool(os.getenv("TAVILY_API_KEY")) and (bool(os.getenv("OPENROUTER_API_KEY")) or bool(os.getenv("GROQ_API_KEY")))

    if st.button("🚀 Run Research", type="primary", disabled=not ready):
        if not product_idea.strip():
            st.error("Enter a product idea.")
        else:
            run_flow(product_idea.strip(), mode)

    if st.session_state.stage == "complete" and st.session_state.results:
        render_results(st.session_state.results)

    if st.session_state.stage == "awaiting_review":
        render_review_ui()


if __name__ == "__main__":
    main()
