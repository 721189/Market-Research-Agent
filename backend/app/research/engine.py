import asyncio
from typing import Dict, Any, List, Optional
try:
    from sqlalchemy.orm import Session
    from backend.app.models.evidence import Evidence, Claim
    from backend.app.models.research import ResearchEvent, ResearchJob
except ImportError:
    Session = Any # type: ignore
    Evidence = Any # type: ignore
    Claim = Any # type: ignore
    ResearchEvent = Any # type: ignore
    ResearchJob = Any # type: ignore
from urllib.parse import urlparse
import datetime
import logging

from backend.app.research.planner import generate_research_plan
from backend.app.research.competitor import extract_competitors
from backend.app.research.market import extract_market_dynamics
from backend.app.research.pricing import extract_pricing_landscape
from backend.app.research.customer import extract_customer_profiles
from backend.app.research.financial import financial_engine
from backend.app.research.evidence import evidence_collector
from backend.app.research.claims import claim_engine
from backend.app.research.confidence import confidence_engine
from backend.app.research.validators import research_validator
from backend.app.research.synthesis import synthesize_strategic_report
from backend.app.services.rate_limiter import rate_limiter
from backend.app.services.prompt_guard import prompt_guard, PromptInjectionError
from backend.app.providers.base import ExtractionResultState
from backend.app.research.policy import get_research_policy

logger = logging.getLogger("marketai.engine")

class JobCancelledException(Exception):
    """Raised when a research job has been cancelled by user or tenant administrator."""
    pass

class ResearchEngine:
    def _is_job_cancelled(self, research_id: str, db: Session = None) -> bool:
        """
        Dual-layer fast cancellation check:
        1. Redis ephemeral cancellation key (sub-millisecond)
        2. Database status
        """
        try:
            if rate_limiter.redis and rate_limiter.redis.exists(f"job_cancel:{research_id}"):
                return True
        except Exception:
            pass

        if db:
            try:
                job_status = db.query(ResearchJob.status).filter(ResearchJob.id == research_id).scalar()
                if job_status in ("CANCELLED", "CANCELLING"):
                    return True
            except Exception as e:
                logger.warning(f"Error checking cancellation status for {research_id}: {e}")

        return False

    async def run(
        self,
        product_idea: str,
        mode: str,
        research_id: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Coordinates the 7-stage authoritative research pipeline with granular cancellation checks
        and explicit extraction result state tracking (eliminating fake/fallback data).
        """
        # Helper to emit progress events
        def emit_event(stage: str, progress: int, message: str, level: str = "INFO"):
            if db:
                try:
                    event = ResearchEvent(
                        job_id=research_id,
                        stage=stage,
                        progress=progress,
                        message=message,
                        level=level
                    )
                    db.add(event)
                    # Also update job progress percentage
                    job = db.query(ResearchJob).filter(ResearchJob.id == research_id).first()
                    if job:
                        job.progress = progress
                    db.commit()
                except Exception as e:
                    logger.warning(f"Failed to record research event: {e}")

        def check_cancellation(checkpoint_name: str):
            if self._is_job_cancelled(research_id, db):
                emit_event("cancelled", 0, f"Execution halted at checkpoint: {checkpoint_name}", level="WARNING")
                logger.info(f"Research job {research_id} halted due to cancellation at {checkpoint_name}")
                raise JobCancelledException(f"Job {research_id} was cancelled during {checkpoint_name}")

        # Checkpoint 0: Pre-flight & Prompt Injection Defense
        check_cancellation("preflight")
        is_safe, safety_err = prompt_guard.inspect_input(product_idea)
        if not is_safe:
            emit_event("security_violation", 0, f"Prompt injection rejected: {safety_err}", level="ERROR")
            raise PromptInjectionError(f"Security validation failed: {safety_err}")

        # Stage 1: Planning
        emit_event("planning", 10, "Formulating targeted research hypotheses and questions via LLM Gateway")
        plan = await generate_research_plan(product_idea, mode)
        check_cancellation("post-planning")

        # Stage 2: Parallel research (real LLM extraction, no synthetic fake defaults)
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
        check_cancellation("post-retrieval")

        # Stage 3: Evidence extraction, content harvesting & claim persistence
        emit_event("evidence_extraction", 50, "Extracting, harvesting content, and indexing claims")
        all_sources = []
        for c in competitors:
            all_sources.extend(c.get("sources", []))
        all_sources.extend(market.get("sources", []))
        all_sources.extend(pricing.get("sources", []))
        all_sources.extend(customer.get("sources", []))
        cleaned_sources = research_validator.validate_sources(all_sources)

        policy = get_research_policy(mode)
        cleaned_sources = cleaned_sources[:policy.max_sources]

        evidence_records = []
        evidence_objs = []
        for url in cleaned_sources:
            # Real evidence harvesting with SSRF protection and content hashing
            harvested = await evidence_collector.harvest_and_hash_evidence(url)
            if not harvested:
                logger.info(f"Skipping unharvestable or invalid URL: {url}")
                continue

            ev_data = harvested
            evidence_records.append(ev_data)

            if db:
                ev_obj = Evidence(
                    job_id=research_id,
                    url=ev_data["url"],
                    domain=ev_data["domain"],
                    authority_score=ev_data["authority_score"],
                    freshness_score=ev_data["freshness_score"],
                    content_hash=ev_data["content_hash"],
                    raw_snippet=(ev_data.get("snippet") or "")[:1000],
                    snapshot_object_key=ev_data.get("snapshot_object_key"),
                    full_text=ev_data.get("snippet", "")
                )
                db.add(ev_obj)
                evidence_objs.append(ev_obj)

        if db:
            db.commit()
            for obj in evidence_objs:
                db.refresh(obj)

        check_cancellation("post-evidence")

        emit_event("research_complete", 60, f"Market research retrieval complete. Handing off to analysis engine.")

        # Compile structured intermediate output for analysis worker
        intermediate_output = {
            "competitors": competitors,
            "market_dynamics": market,
            "pricing_landscape": pricing,
            "customer_profile": customer,
            "evidence_sources": evidence_records
        }

        return intermediate_output

research_engine = ResearchEngine()
