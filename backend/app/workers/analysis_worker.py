import asyncio
import datetime
import logging
from celery.utils.log import get_task_logger
from backend.app.workers.celery_app import celery_app
from backend.app.db.session import SessionLocal
from backend.app.models.research import ResearchJob, ResearchRun, ResearchEvent
from backend.app.models.evidence import Evidence, Claim
from backend.app.research.claims import claim_engine
from backend.app.research.agreement import agreement_engine
from backend.app.research.financial import financial_engine
from backend.app.research.confidence import confidence_engine
from backend.app.research.synthesis import synthesize_strategic_report
from backend.app.providers.base import ExtractionResultState
from backend.app.services.cost import cost_service
from backend.app.services.entitlement import entitlement_service

logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, acks_late=True)
def analyze_evidence_task(self, job_id: str):
    """
    Authoritative 8-stage analysis pipeline:
    1. Claim Extraction: Extract structured claims with quotes and source references
    2. Claim Validation & Evidence Linking: Match claims against collected Evidence rows
    3. Cross-Source Concordance: Compute empirical agreement across distinct domains
    4. Conflict & Discrepancy Detection: Flag pricing/market contradictions
    5. Financial Sensitivity Modeling: Run deterministic unit economics and break-even scenarios
    6. Empirical Confidence Scoring: Combine authority, freshness, coverage, and agreement
    7. Strategic Synthesis: Generate executive summary, SWOT, and GTM strategy
    8. Dataset Compilation & Quota Finalization: Persist enriched result and chain to PDF worker
    """
    db = SessionLocal()
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job or job.status == "CANCELLED":
        db.close()
        return

    run_record = ResearchRun(
        job_id=job_id,
        stage="analysis",
        status="RUNNING",
        worker_id=str(self.request.id)
    )
    db.add(run_record)

    def emit_event(stage: str, progress: int, message: str, level: str = "INFO"):
        try:
            evt = ResearchEvent(
                job_id=job.id,
                stage=stage,
                progress=progress,
                message=message,
                level=level
            )
            db.add(evt)
            job.progress = progress
            db.commit()
        except Exception as err:
            logger.warning(f"Failed to emit analysis event for {job_id}: {err}")

    try:
        job.status = "ANALYZING"
        db.commit()

        # Retrieve existing intermediate data or evidence records
        raw_result = job.result or {}
        evidence_objs = db.query(Evidence).filter(Evidence.job_id == job_id).all()
        
        evidence_records = [
            {
                "url": ev.url,
                "domain": ev.domain,
                "authority_score": ev.authority_score,
                "freshness_score": ev.freshness_score,
                "content_hash": ev.content_hash,
                "title": ev.title,
                "snippet": ev.snapshot_object_key or ev.url
            }
            for ev in evidence_objs
        ] if evidence_objs else raw_result.get("evidence_sources", [])

        competitors = raw_result.get("competitors", [])
        market = raw_result.get("market_dynamics", {})
        pricing = raw_result.get("pricing_landscape", {})
        customer = raw_result.get("customer_profile", {})
        product_idea = job.product_idea

        # Stage 1: Structured Claim Extraction
        emit_event("claim_extraction", 72, "Extracting verifiable factual and quantitative claims from evidence")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            extracted_claims = loop.run_until_complete(
                claim_engine.extract_claims_from_evidence(
                    product_idea=product_idea,
                    evidence_records=evidence_records,
                    research_context={
                        "market_dynamics": market,
                        "pricing_landscape": pricing,
                        "competitors": competitors,
                        "customer": customer
                    }
                )
            )
        finally:
            loop.close()

        # Stage 2: Claim Validation & DB Linking
        emit_event("claim_validation", 76, "Validating extracted claims and establishing source provenance graph")
        persisted_claims = claim_engine.persist_claims_and_link_evidence(
            db=db,
            job_id=job_id,
            claims_data=extracted_claims,
            evidence_objs=evidence_objs
        )

        # Stage 3 & 4: Cross-Source Concordance and Conflict Detection
        emit_event("cross_validation", 80, "Evaluating cross-source concordance and scanning for discrepancies")
        agreement_data = agreement_engine.compute_agreement(
            sources=evidence_records,
            competitors=competitors,
            claims=persisted_claims,
            pricing_points=[]
        )

        # Stage 5: Financial Sensitivity Modeling
        emit_event("financial_modeling", 84, "Executing multi-scenario unit economics and sensitivity matrix")
        raw_price = pricing.get("mid_tier_usd") or pricing.get("entry_tier_usd")
        if raw_price is not None and isinstance(raw_price, (int, float)) and raw_price > 0:
            suggested_price = float(raw_price)
            pricing_basis = "extracted_market_data"
        else:
            suggested_price = 49.0
            pricing_basis = "standard_benchmark_baseline"

        estimated_cogs = round(suggested_price * 0.28, 2)
        financial_scenarios = financial_engine.generate_scenarios(suggested_price, estimated_cogs)
        financial_scenarios["assumptions"]["pricing_basis"] = pricing_basis
        base_fin = financial_scenarios["base_case"]

        # Stage 6: Empirical Confidence Calculation
        emit_event("confidence_scoring", 88, "Computing observable evidence confidence score")
        confidence_result = confidence_engine.calculate_confidence(
            sources=evidence_records,
            claims_count=len(persisted_claims),
            competitors=competitors,
            claims=persisted_claims,
            calculation_valid=True
        )

        # Stage 7: Strategic Synthesis
        emit_event("synthesis", 92, "Synthesizing executive brief and management strategy")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            synthesis = loop.run_until_complete(
                synthesize_strategic_report(
                    product_idea, competitors, market, pricing, customer, base_fin
                )
            )
        finally:
            loop.close()

        # Stage 8: Final Research Dataset Compilation
        emit_event("compilation", 96, "Assembling authoritative research dataset with complete claim provenance")
        
        sub_states = [
            market.get("extraction_state", "UNKNOWN"),
            pricing.get("extraction_state", "UNKNOWN"),
            customer.get("extraction_state", "UNKNOWN"),
            synthesis.get("synthesis_state", "UNKNOWN"),
        ]
        if all(s == ExtractionResultState.SUCCESS.value for s in sub_states) and len(competitors) > 0:
            pipeline_state = ExtractionResultState.SUCCESS.value
        elif any(s == ExtractionResultState.SUCCESS.value for s in sub_states) or len(competitors) > 0:
            pipeline_state = ExtractionResultState.PARTIAL.value
        else:
            pipeline_state = ExtractionResultState.FAILED.value

        final_dataset = {
            "product_idea": product_idea,
            "mode": job.mode,
            "pipeline_state": pipeline_state,
            "executive_summary": synthesis.get("executive_summary", ""),
            "strategic_recommendations": synthesis.get("strategic_recommendations", []),
            "swot_analysis": synthesis.get("swot_analysis", {}),
            "go_to_market": synthesis.get("go_to_market", {}),
            "market_dynamics": market,
            "competitors": competitors,
            "customer_profile": customer,
            "pricing_landscape": pricing,
            "claims": persisted_claims,
            "cross_source_agreement": agreement_data,
            "financials": {
                "estimated_cogs": base_fin["cogs"],
                "suggested_retail_price": base_fin["selling_price"],
                "projected_margin_percentage": base_fin["gross_margin_percentage"],
                "markup_percentage": base_fin["markup_percentage"],
                "break_even_units": base_fin["break_even_units_monthly"],
                "pricing_basis": pricing_basis,
                "scenarios": financial_scenarios
            },
            "confidence": confidence_result,
            "evidence_sources": evidence_records
        }

        job.result = final_dataset
        job.progress = 98
        run_record.status = "COMPLETED"
        run_record.completed_at = datetime.datetime.utcnow()
        db.commit()

        # Commit quota reservation as successfully consumed
        entitlement_service.commit_quota(db, job_id, units=1, billing_rule="standard")

        # Chain to PDF worker
        from backend.app.workers.pdf_worker import generate_pdf_report_task
        generate_pdf_report_task.apply_async(args=[job_id], queue="reports")

    except Exception as e:
        logger.exception(f"Error in analysis worker for job {job_id}: {e}")
        job.status = "FAILED"
        job.error_code = "ANALYSIS_ERROR"
        job.error_message = str(e)
        run_record.status = "FAILED"
        run_record.error_message = str(e)
        
        # Release quota if failed
        entitlement_service.release_quota(db, job_id, reason="failed_during_analysis")
        db.commit()
        raise self.retry(exc=e)
    finally:
        db.close()
