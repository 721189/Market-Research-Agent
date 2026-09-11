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

from backend.app.research.engine import JobCancelledException

logger = get_task_logger(__name__)

# Non-retryable permanent failure types
FATAL_EXCEPTIONS = (
    JobCancelledException,
    ValueError,
    KeyError,
    PermissionError,
)

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

    def check_cancellation(checkpoint_name: str):
        from backend.app.services.rate_limiter import rate_limiter
        is_cancelled = False
        try:
            if rate_limiter.redis and rate_limiter.redis.exists(f"job_cancel:{job_id}"):
                is_cancelled = True
        except:
            pass
        if not is_cancelled:
            job_status = db.query(ResearchJob.status).filter(ResearchJob.id == job_id).scalar()
            if job_status in ("CANCELLED", "CANCELLING"):
                is_cancelled = True
        
        if is_cancelled:
            emit_event("cancelled", job.progress, f"Analysis halted at checkpoint: {checkpoint_name}", level="WARNING")
            raise JobCancelledException(f"Job {job_id} cancelled during {checkpoint_name}")

    try:
        from backend.app.research.policy import get_research_policy
        policy = get_research_policy(job.mode)
        cost_service.start_job_metering(
            job_id,
            max_llm_calls=policy.max_llm_calls,
            max_context_tokens=policy.max_context_tokens
        )

        check_cancellation("pre_analysis")
        job.status = "ANALYZING"
        db.commit()

        # Retrieve existing intermediate data or evidence records
        raw_result = job.result or {}
        evidence_objs = db.query(Evidence).filter(Evidence.job_id == job_id).all()
        
        evidence_records = []
        if evidence_objs:
            from backend.app.services.storage import storage_service
            for ev in evidence_objs:
                text_content = None
                if ev.snapshot_object_key:
                    try:
                        raw_b = storage_service.get_object_bytes(ev.snapshot_object_key)
                        if raw_b:
                            text_content = raw_b.decode("utf-8", errors="ignore")
                            ev.full_text = text_content
                    except Exception as err:
                        logger.warning(f"Failed to load snapshot object {ev.snapshot_object_key}: {err}")
                
                if not text_content:
                    text_content = ev.full_text or ev.raw_snippet or ""
                
                evidence_records.append({
                    "url": ev.url,
                    "domain": ev.domain,
                    "authority_score": ev.authority_score,
                    "freshness_score": ev.freshness_score,
                    "content_hash": ev.content_hash,
                    "title": ev.title,
                    "snippet": text_content if text_content else ev.url,
                    "snapshot_object_key": ev.snapshot_object_key
                })
        else:
            evidence_records = raw_result.get("evidence_sources", [])

        competitors = raw_result.get("competitors", [])
        market = raw_result.get("market_dynamics", {})
        pricing = raw_result.get("pricing_landscape", {})
        customer = raw_result.get("customer_profile", {})
        product_idea = job.product_idea

        # Stage 1: Structured Claim Retrieval or Extraction (Single Authoritative Source)
        emit_event("claim_extraction", 72, "Loading and validating structured claims from evidence")
        
        existing_claims = db.query(Claim).filter(Claim.job_id == job_id).all()
        if existing_claims:
            persisted_claims = [
                {
                    "claim_text": c.claim_text,
                    "claim_type": c.claim_type,
                    "value": c.value,
                    "unit": c.unit,
                    "confidence": c.confidence,
                    "verification_status": c.verification_status,
                    "agreement_ratio": c.agreement_ratio,
                    "sources": [src.url for src in c.sources] if c.sources else []
                }
                for c in existing_claims
            ]
            extracted_claims = persisted_claims
        else:
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
        check_cancellation("pre_concordance")
        emit_event("cross_validation", 80, "Evaluating cross-source concordance and scanning for discrepancies")
        agreement_data = agreement_engine.compute_agreement(
            sources=evidence_records,
            competitors=competitors,
            claims=persisted_claims,
            pricing_points=[]
        )

        # Stage 5: Financial Sensitivity Modeling
        check_cancellation("pre_financial_modeling")
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
        check_cancellation("pre_synthesis")
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
                "assumption_type": "benchmark_assumption" if pricing_basis == "standard_benchmark_baseline" else "extracted_market_evidence",
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

        # Finalize accumulated LLM usage and cost metering
        try:
            cost_service.finalize_job_usage(db=db, org_id=job.org_id, job_id=job_id, user_id=job.user_id)
        except Exception as meter_err:
            logger.warning(f"Could not finalize job usage metrics: {meter_err}")

        # Commit quota reservation as successfully consumed
        entitlement_service.commit_quota(db, job_id, units=1, billing_rule="standard")

        # Chain to PDF worker
        from backend.app.workers.pdf_worker import generate_pdf_report_task
        generate_pdf_report_task.apply_async(args=[job_id], queue="reports")

    except JobCancelledException as e:
        logger.info(f"Analysis job {job_id} successfully terminated upon cancellation request: {e}")
        try:
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if job:
                job.status = "CANCELLED"
                job.cancelled_at = datetime.datetime.utcnow()
            run = db.query(ResearchRun).filter(ResearchRun.job_id == job_id, ResearchRun.status == "RUNNING").first()
            if run:
                run.status = "CANCELLED"
                run.completed_at = datetime.datetime.utcnow()
            db.commit()
            entitlement_service.release_quota(db, job_id, reason="job_cancelled")
        except Exception as db_err:
            logger.error(f"Error updating cancellation status for job {job_id}: {db_err}")
            
    except Exception as e:
        logger.exception(f"Error in analysis worker for job {job_id}: {e}")
        is_fatal = isinstance(e, FATAL_EXCEPTIONS) or self.request.retries >= self.max_retries
        
        if is_fatal:
            job.status = "FAILED"
            job.error_code = "ANALYSIS_ERROR"
            job.error_message = str(e)
            run_record.status = "FAILED"
            run_record.error_message = str(e)
            # Release reserved quota permanently on final failure
            entitlement_service.release_quota(db, job_id, reason="failed_during_analysis")
            db.commit()
        else:
            job.status = "RETRYING"
            run_record.status = "RETRYING"
            db.commit()
            raise self.retry(exc=e)
    finally:
        db.close()
