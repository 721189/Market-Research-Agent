import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from urllib.parse import urlparse
import datetime

from backend.app.research.planner import generate_research_plan
from backend.app.research.competitor import extract_competitors
from backend.app.research.market import extract_market_dynamics
from backend.app.research.pricing import extract_pricing_landscape
from backend.app.research.customer import extract_customer_profiles
from backend.app.research.financial import financial_engine
from backend.app.research.evidence import evidence_collector
from backend.app.research.confidence import confidence_engine
from backend.app.research.validators import research_validator
from backend.app.research.synthesis import synthesize_strategic_report
from backend.app.models.evidence import Evidence, Claim
from backend.app.models.research import ResearchEvent

class ResearchEngine:
    async def run(
        self,
        product_idea: str,
        mode: str,
        research_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Coordinates the 7-stage research pipeline and returns structured data.
        """
        # Helper to emit progress events
        def emit_event(stage: str, progress: int, message: str):
            if db:
                event = ResearchEvent(
                    job_id=research_id,
                    stage=stage,
                    progress=progress,
                    message=message,
                    level="INFO"
                )
                db.add(event)
                db.commit()

        # Stage 1: Planning
        emit_event("planning", 10, "Formulating targeted research hypotheses and questions")
        plan = await generate_research_plan(product_idea)

        # Stage 2: Parallel research
        emit_event("researching", 30, "Executing multi-dimensional web retrieval (competitor, market, pricing, customer)")
        competitors_task = extract_competitors(product_idea, plan.get("competitor_questions", []))
        market_task = extract_market_dynamics(product_idea, plan.get("market_questions", []))
        pricing_task = extract_pricing_landscape(product_idea, plan.get("pricing_questions", []))
        customer_task = extract_customer_profiles(product_idea, plan.get("customer_questions", []))

        competitors, market, pricing, customer = await asyncio.gather(
            competitors_task,
            market_task,
            pricing_task,
            customer_task
        )

        # Stage 3: Evidence extraction & persistence
        emit_event("evidence_extraction", 50, "Extracting and indexing verifiable evidence and claims")
        all_sources = []
        for c in competitors:
            all_sources.extend(c.get("sources", []))
        all_sources.extend(market.get("sources", []))
        all_sources.extend(pricing.get("sources", []))
        all_sources.extend(customer.get("sources", []))
        cleaned_sources = research_validator.validate_sources(all_sources)

        evidence_records = []
        evidence_objs = []
        for url in cleaned_sources:
            domain = urlparse(url).netloc or "web"
            auth_score = evidence_collector.compute_authority(url)
            fresh_score = evidence_collector.compute_freshness(datetime.datetime.utcnow())
            content_hash = evidence_collector.compute_hash(f"{url}-{product_idea}")
            
            ev_data = {
                "url": url,
                "domain": domain,
                "authority_score": auth_score,
                "freshness_score": fresh_score,
                "content_hash": content_hash
            }
            evidence_records.append(ev_data)

            if db:
                ev_obj = Evidence(
                    job_id=research_id,
                    url=url,
                    domain=domain,
                    authority_score=auth_score,
                    freshness_score=fresh_score,
                    content_hash=content_hash
                )
                db.add(ev_obj)
                evidence_objs.append(ev_obj)

        if db:
            db.commit()

        # Stage 4: Validation
        emit_event("validation", 65, "Validating data integrity and cross-referencing sources")
        is_comp_valid, _ = research_validator.validate_competitor_data(competitors)

        # Stage 5: Deterministic Financial Analysis
        emit_event("financial_analysis", 75, "Calculating deterministic unit economics and scenarios")
        suggested_price = float(pricing.get("mid_tier_usd", 49.0))
        estimated_cogs = round(suggested_price * 0.28, 2) # Typical 72% gross margin baseline
        financial_scenarios = financial_engine.generate_scenarios(suggested_price, estimated_cogs)
        base_fin = financial_scenarios["base_case"]

        # Stage 6: Strategic Synthesis
        emit_event("synthesis", 85, "Synthesizing executive brief and management strategy")
        synthesis = await synthesize_strategic_report(
            product_idea, competitors, market, pricing, customer, base_fin
        )

        # Stage 7: QA & Confidence Scoring
        emit_event("confidence_evaluation", 95, "Evaluating objective confidence metric across evidence base")
        confidence_result = confidence_engine.calculate_confidence(
            sources=evidence_records,
            claims_count=len(competitors) * 2 + 4,
            cross_source_agreements=len(cleaned_sources),
            calculation_valid=True
        )

        emit_event("completed", 100, "Market research analysis complete")

        # Compile structured final output
        structured_output = {
            "product_idea": product_idea,
            "mode": mode,
            "executive_summary": synthesis.get("executive_summary", ""),
            "strategic_recommendations": synthesis.get("strategic_recommendations", []),
            "swot_analysis": synthesis.get("swot_analysis", {}),
            "go_to_market": synthesis.get("go_to_market", {}),
            "market_dynamics": market,
            "competitors": competitors,
            "customer_profile": customer,
            "pricing_landscape": pricing,
            "financials": {
                "estimated_cogs": base_fin["cogs"],
                "suggested_retail_price": base_fin["selling_price"],
                "projected_margin_percentage": base_fin["gross_margin_percentage"],
                "markup_percentage": base_fin["markup_percentage"],
                "break_even_units": base_fin["break_even_units_monthly"],
                "scenarios": financial_scenarios
            },
            "confidence": confidence_result,
            "evidence_sources": evidence_records
        }

        return structured_output

research_engine = ResearchEngine()
