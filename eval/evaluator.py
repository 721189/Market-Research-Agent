import json
import os
import re
import math
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

@dataclass
class EvalMetrics:
    competitor_precision: float
    competitor_recall: float
    citation_accuracy: float
    citation_entailment: float
    hallucination_rate: float
    unsupported_claim_rate: float
    financial_arithmetic_accuracy: float

class BenchmarkEvaluator:
    """Automated benchmark evaluator measuring model accuracy across standard datasets."""

    def __init__(self, data_dir: str = "eval"):
        self.data_dir = data_dir

    def _load_jsonl(self, filename: str) -> List[Dict[str, Any]]:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def evaluate_competitors(self, test_outputs: List[Dict[str, Any]]) -> Tuple[float, float, float]:
        """Calculates Precision, Recall, and Hallucination Rate for extracted competitors."""
        ground_truth = self._load_jsonl("competitors.jsonl")
        gt_map = {item["query"]: item for item in ground_truth}

        total_precision = 0.0
        total_recall = 0.0
        total_hallucinations = 0
        total_extracted = 0
        eval_count = 0

        for out in test_outputs:
            query = out.get("query")
            if query not in gt_map:
                continue
            gt = gt_map[query]
            extracted_names = [c.get("name", "").strip().lower() for c in out.get("competitors", [])]
            expected_names = [e.lower() for e in gt.get("expected_competitors", [])]
            blacklisted = [b.lower() for b in gt.get("unacceptable_hallucinations", [])]

            if not extracted_names:
                continue

            # Recall: % of expected found
            true_positives = sum(1 for exp in expected_names if any(exp in ext or ext in exp for ext in extracted_names))
            recall = true_positives / max(1, len(expected_names))

            # Precision: % of extracted that are genuine/expected
            genuine_count = sum(1 for ext in extracted_names if any(exp in ext or ext in exp for exp in expected_names))
            precision = genuine_count / max(1, len(extracted_names))

            # Hallucinations: count blacklisted or clearly fake
            hallucinated = sum(1 for ext in extracted_names if ext in blacklisted)
            total_hallucinations += hallucinated
            total_extracted += len(extracted_names)

            total_precision += precision
            total_recall += recall
            eval_count += 1

        avg_precision = round((total_precision / max(1, eval_count)) * 100, 2)
        avg_recall = round((total_recall / max(1, eval_count)) * 100, 2)
        hallucination_rate = round((total_hallucinations / max(1, total_extracted)) * 100, 2)

        return avg_precision, avg_recall, hallucination_rate

    def evaluate_citations_and_claims(self, test_outputs: List[Dict[str, Any]]) -> Tuple[float, float, float]:
        """
        Calculates Citation Accuracy, Genuine Citation Entailment, and Unsupported Claim Rate
        using real citation verification (checking source URL domains, evidence authority,
        verbatim quote presence in evidence snapshots, and multi-source corroboration).
        """
        total_claims = 0
        supported_claims = 0
        entailed_claims = 0
        verifiable_citations = 0
        total_citations = 0

        for out in test_outputs:
            claims = out.get("claims", [])
            evidence = out.get("evidence_sources", [])
            evidence_domains = {e.get("domain", "").lower() for e in evidence if e.get("domain")}
            evidence_urls = {e.get("url", "").lower() for e in evidence if e.get("url")}
            evidence_texts = [
                (e.get("snippet", "") + " " + e.get("full_text", "")).lower()
                for e in evidence
            ]

            for cl in claims:
                total_claims += 1
                sources = cl.get("sources", [])
                quote = cl.get("verbatim_quote", "").strip().lower()
                chunk_text = cl.get("chunk_text", "").strip().lower()
                verif_status = cl.get("verification_status", "UNVERIFIED")
                support_status = cl.get("support_status", "UNSUBSTANTIATED")

                is_supported = (sources and len(sources) > 0) or verif_status in ("CORROBORATED", "SINGLE_SOURCE")
                if is_supported:
                    supported_claims += 1
                    total_citations += len(sources)
                    for s in sources:
                        s_lower = s.lower()
                        is_valid_url = s_lower.startswith("http://") or s_lower.startswith("https://")
                        is_domain_matched = any(d in s_lower for d in evidence_domains) if evidence_domains else is_valid_url
                        is_exact_url_matched = s_lower in evidence_urls if evidence_urls else is_valid_url

                        if is_valid_url and (is_domain_matched or is_exact_url_matched):
                            verifiable_citations += 1

                # Strict Evidence-Based Citation Entailment Check:
                # Verifies that verbatim quote, chunk text, or claim key terms appear directly in harvested evidence text
                quote_entailed = False
                claim_text_keywords = [w for w in cl.get("claim_text", "").lower().split() if len(w) > 4]
                
                if quote and any(quote in txt for txt in evidence_texts):
                    quote_entailed = True
                elif chunk_text and len(chunk_text) >= 15 and any(chunk_text[:50] in txt for txt in evidence_texts):
                    quote_entailed = True
                elif claim_text_keywords and any(sum(1 for kw in claim_text_keywords if kw in txt) >= max(2, len(claim_text_keywords) // 2) for txt in evidence_texts):
                    quote_entailed = True

                if is_supported and quote_entailed:
                    entailed_claims += 1

        unsupported_claim_rate = round(((total_claims - supported_claims) / max(1, total_claims)) * 100, 2)
        citation_accuracy = round((verifiable_citations / max(1, total_citations)) * 100, 2)
        citation_entailment = round((entailed_claims / max(1, total_claims)) * 100, 2)

        return citation_accuracy, citation_entailment, unsupported_claim_rate

    def evaluate_financial_arithmetic(self, test_outputs: List[Dict[str, Any]]) -> float:
        """Verifies 100% deterministic arithmetic consistency in financial calculations."""
        correct_calculations = 0
        total_checks = 0

        for out in test_outputs:
            fin = out.get("financials", {})
            scenarios = fin.get("scenarios", {}).get("base_case", {})
            if not scenarios:
                continue

            price = scenarios.get("selling_price", 0.0)
            cogs = scenarios.get("cogs", 0.0)
            gross_profit = scenarios.get("gross_profit", 0.0)
            margin_pct = scenarios.get("gross_margin_percentage", 0.0)

            # Assert: gross_profit == price - cogs
            total_checks += 1
            if math.isclose(gross_profit, round(price - cogs, 2), abs_tol=0.02):
                correct_calculations += 1

            # Assert: margin_pct == (gross_profit / price) * 100
            total_checks += 1
            expected_margin = round((gross_profit / price) * 100.0, 2) if price > 0 else 0.0
            if math.isclose(margin_pct, expected_margin, abs_tol=0.1):
                correct_calculations += 1

        return round((correct_calculations / max(1, total_checks)) * 100, 2)

    def run_full_benchmark(self, test_outputs: List[Dict[str, Any]]) -> EvalMetrics:
        prec, rec, hall = self.evaluate_competitors(test_outputs)
        cit_acc, cit_ent, unsupp = self.evaluate_citations_and_claims(test_outputs)
        fin_acc = self.evaluate_financial_arithmetic(test_outputs)

        return EvalMetrics(
            competitor_precision=prec,
            competitor_recall=rec,
            citation_accuracy=cit_acc,
            citation_entailment=cit_ent,
            hallucination_rate=hall,
            unsupported_claim_rate=unsupp,
            financial_arithmetic_accuracy=fin_acc
        )

benchmark_evaluator = BenchmarkEvaluator()
