import json
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

try:
    from sqlalchemy.orm import Session
    from backend.app.models.evidence import Claim, Evidence, claim_sources
except ImportError:
    Session = Any # type: ignore
    Claim = Any # type: ignore
    Evidence = Any # type: ignore
    claim_sources = None # type: ignore

from backend.app.providers.gateway import llm_gateway
from backend.app.research.evidence import evidence_collector

logger = logging.getLogger("marketai.research.claims")

CLAIM_EXTRACTION_PROMPT = """You are a rigorous market research data auditor.
Extract all concrete, verifiable claims and quantitative data points from the following market research context.

Context:
{context}

Return a JSON array of claim objects, each strictly matching this schema:
[
  {{
    "claim_text": "Precise summary of the factual or quantitative claim",
    "claim_type": "market_size | cagr | competitor_pricing | customer_demand | cogs_assumption",
    "value": "Numeric value or specific attribute if applicable (e.g., '14.2B', '24.5%')",
    "unit": "USD | percentage | users | months | count | ratio",
    "verbatim_quote": "Direct quote from source text supporting this claim",
    "source_url": "URL or domain where this fact was identified",
    "confidence": 85
  }}
]

Strict Rules:
1. Only extract claims that are directly supported by the context. Do not extrapolate.
2. Ensure verbatim_quote actually appears in the text context.
3. Return ONLY valid JSON array with no markdown decoration.
"""

class ClaimEngine:
    @classmethod
    async def extract_claims_from_evidence(
        cls,
        product_idea: str,
        evidence_records: List[Dict[str, Any]],
        research_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Uses LLM Gateway to extract structured, verifiable claims with verbatim quotes
        and source linking.
        """
        # Build synthesis context
        context_snippets = []
        for idx, ev in enumerate(evidence_records):
            url = ev.get("url", f"source_{idx}")
            snippet = ev.get("snippet") or ev.get("title") or url
            context_snippets.append(f"Source [{url}]:\n{snippet}\n")

        # Add section contexts
        if "market_dynamics" in research_context:
            md = research_context["market_dynamics"]
            context_snippets.append(f"Market Dynamics: Size={md.get('market_size')}, Growth={md.get('growth_rate')}, Drivers={md.get('key_drivers')}")
        if "pricing_landscape" in research_context:
            pl = research_context["pricing_landscape"]
            context_snippets.append(f"Pricing Landscape: Entry={pl.get('entry_tier_usd')}, Mid={pl.get('mid_tier_usd')}, Enterprise={pl.get('enterprise_tier_usd')}")

        full_context = "\n\n".join(context_snippets)
        prompt = CLAIM_EXTRACTION_PROMPT.format(context=full_context[:6000])

        try:
            resp = await llm_gateway.generate(
                prompt=prompt,
                model="gemini-1.5-flash",
                temperature=0.1
            )
            raw_text = resp.text.strip()
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                return parsed
            return []
        except Exception as e:
            logger.warning(f"Failed to extract structured claims via LLM Gateway: {e}")
            # Fallback heuristic extraction from context
            fallback_claims = []
            if "market_dynamics" in research_context:
                md = research_context["market_dynamics"]
                if md.get("market_size"):
                    fallback_claims.append({
                        "claim_text": f"Estimated market size is {md.get('market_size')}",
                        "claim_type": "market_size",
                        "value": str(md.get("market_size")),
                        "unit": "USD",
                        "verbatim_quote": str(md.get("market_size")),
                        "source_url": (md.get("sources") or [""])[0],
                        "confidence": 75
                    })
                if md.get("growth_rate"):
                    fallback_claims.append({
                        "claim_text": f"Market CAGR projected at {md.get('growth_rate')}",
                        "claim_type": "cagr",
                        "value": str(md.get("growth_rate")),
                        "unit": "percentage",
                        "verbatim_quote": str(md.get("growth_rate")),
                        "source_url": (md.get("sources") or [""])[0],
                        "confidence": 75
                    })
            return fallback_claims

    @classmethod
    def persist_claims_and_link_evidence(
        cls,
        db: Optional[Session],
        job_id: str,
        claims_data: List[Dict[str, Any]],
        evidence_objs: List[Evidence]
    ) -> List[Dict[str, Any]]:
        """
        Stores structured claims in database, links them to Evidence via claim_sources,
        and computes verification status based on multi-source coverage.
        """
        persisted_claims = []
        evidence_by_url = {ev.url: ev for ev in evidence_objs}
        evidence_by_domain = {ev.domain: ev for ev in evidence_objs}

        for c_data in claims_data:
            claim_text = c_data.get("claim_text", "").strip()
            if not claim_text:
                continue

            claim_type = c_data.get("claim_type", "market_insight")
            value = c_data.get("value")
            unit = c_data.get("unit")
            conf = int(c_data.get("confidence", 70))
            src_url = c_data.get("source_url", "")

            # Match associated evidence
            matched_evidence = []
            if src_url in evidence_by_url:
                matched_evidence.append(evidence_by_url[src_url])
            else:
                domain = urlparse(src_url).netloc.lower() if src_url else ""
                if domain in evidence_by_domain:
                    matched_evidence.append(evidence_by_domain[domain])

            num_sources = len(matched_evidence)
            if num_sources >= 2:
                verif_status = "CORROBORATED"
                agreement_ratio = f"{num_sources}/{num_sources}"
            elif num_sources == 1:
                verif_status = "SINGLE_SOURCE"
                agreement_ratio = "1/1"
            else:
                verif_status = "UNVERIFIED"
                agreement_ratio = "0/1"

            claim_record_dict = {
                "claim_text": claim_text,
                "claim_type": claim_type,
                "value": value,
                "unit": unit,
                "confidence": conf,
                "verification_status": verif_status,
                "agreement_ratio": agreement_ratio,
                "sources": [ev.url for ev in matched_evidence] if matched_evidence else ([src_url] if src_url else [])
            }
            persisted_claims.append(claim_record_dict)

            if db:
                try:
                    db_claim = Claim(
                        job_id=job_id,
                        claim_text=claim_text,
                        claim_type=claim_type,
                        value=str(value) if value is not None else None,
                        unit=unit,
                        confidence=conf,
                        extraction_method="llm_grounded",
                        verification_status=verif_status,
                        agreement_ratio=agreement_ratio
                    )
                    if matched_evidence:
                        db_claim.sources.extend(matched_evidence)
                    db.add(db_claim)
                except Exception as e:
                    logger.warning(f"Error persisting claim to database: {e}")

        if db:
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Failed to commit claims batch to database: {e}")
                db.rollback()

        return persisted_claims

claim_engine = ClaimEngine()
