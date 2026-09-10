from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse
import re
import math
import logging

logger = logging.getLogger("marketai.research.agreement")

class CrossSourceAgreementEngine:
    """
    Evaluates empirical cross-source agreement across claims, competitor profiles,
    and pricing figures reported by distinct evidence domains.
    """

    @staticmethod
    def _extract_domain(url_or_domain: str) -> str:
        if not url_or_domain:
            return "unknown"
        if "://" in url_or_domain:
            try:
                netloc = urlparse(url_or_domain).netloc.lower()
                if ":" in netloc:
                    netloc = netloc.split(":")[0]
                parts = netloc.split(".")
                return ".".join(parts[-2:]) if len(parts) >= 2 else netloc
            except Exception:
                return "unknown"
        return url_or_domain.lower()

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Extracts significant normalized word tokens (filtering common stopwords)."""
        stopwords = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "is", "are", "was", "were", "be", "been", "that",
            "this", "which", "it", "as", "their", "they", "we", "our", "you"
        }
        tokens = re.findall(r'[a-zA-Z0-9]{3,}', text.lower())
        return set(t for t in tokens if t not in stopwords)

    @classmethod
    def evaluate_pricing_agreement(
        cls,
        competitor_price_points: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str], List[str]]:
        """
        Evaluates price points reported for common competitors across multiple sources.
        Returns: (agreements, contradictions, agreement_notes, contradiction_notes)
        """
        agreements = 0
        contradictions = 0
        agreement_notes: List[str] = []
        contradiction_notes: List[str] = []

        # Group prices by competitor name
        by_competitor: Dict[str, List[Tuple[float, str]]] = {}
        for item in competitor_price_points:
            name = (item.get("competitor_name") or "").strip().lower()
            price = item.get("price")
            source = item.get("source_url") or item.get("domain") or "unknown"
            if name and isinstance(price, (int, float)) and price > 0:
                by_competitor.setdefault(name, []).append((float(price), source))

        for name, reports in by_competitor.items():
            if len(reports) < 2:
                continue

            # Compare prices across distinct sources
            prices = [r[0] for r in reports]
            sources = [cls._extract_domain(r[1]) for r in reports]
            unique_sources = set(sources)

            if len(unique_sources) >= 2:
                min_p, max_p = min(prices), max(prices)
                avg_p = sum(prices) / len(prices)
                ratio = (max_p - min_p) / max(1.0, avg_p)

                if ratio <= 0.20:
                    # Prices agree within 20%
                    agreements += 1
                    agreement_notes.append(
                        f"Consistent pricing reported for '{name.title()}' (${min_p:.2f} - ${max_p:.2f}) across {len(unique_sources)} sources."
                    )
                elif ratio >= 0.70:
                    # High pricing divergence / contradiction
                    contradictions += 1
                    contradiction_notes.append(
                        f"Pricing conflict for '{name.title()}': prices range from ${min_p:.2f} to ${max_p:.2f} (>{int(ratio*100)}% variance)."
                    )

        return agreements, contradictions, agreement_notes, contradiction_notes

    @classmethod
    def evaluate_claim_concordance(
        cls,
        claims: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        """
        Evaluates semantic concordance among extracted qualitative claims across independent domains.
        """
        agreements = 0
        contradictions = 0
        notes: List[str] = []

        if len(claims) < 2:
            return 0, 0, notes

        # Compare claim pairs across different sources
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                domain1 = cls._extract_domain(c1.get("source_url") or c1.get("source") or "")
                domain2 = cls._extract_domain(c2.get("source_url") or c2.get("source") or "")

                # Only count agreements across distinct domains
                if domain1 == domain2 or domain1 == "unknown" or domain2 == "unknown":
                    continue

                text1 = c1.get("text") or c1.get("claim") or ""
                text2 = c2.get("text") or c2.get("claim") or ""

                tokens1 = cls._tokenize(text1)
                tokens2 = cls._tokenize(text2)

                if not tokens1 or not tokens2:
                    continue

                intersection = len(tokens1.intersection(tokens2))
                union = len(tokens1.union(tokens2))
                jaccard = intersection / max(1, union)

                # Check for negation patterns (contradiction)
                negation_words = {"not", "never", "no", "lacks", "absent", "without", "fails"}
                has_neg1 = bool(tokens1.intersection(negation_words))
                has_neg2 = bool(tokens2.intersection(negation_words))

                if jaccard >= 0.25:
                    if has_neg1 != has_neg2 and jaccard >= 0.35:
                        contradictions += 1
                    else:
                        agreements += 1
                        notes.append(f"Multi-source claim corroboration between {domain1} and {domain2}")

        return agreements, contradictions, notes

    @classmethod
    def compute_agreement(
        cls,
        sources: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]],
        claims: Optional[List[Dict[str, Any]]] = None,
        pricing_points: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive cross-source agreement evaluation.
        Produces concordance score [0 - 100], agreement count, and contradiction log.
        """
        claims = claims or []
        pricing_points = pricing_points or []

        # If explicit pricing points not provided, extract from competitors
        if not pricing_points and competitors:
            for c in competitors:
                price = c.get("pricing") or c.get("price")
                source = c.get("source_url") or c.get("domain") or ""
                if isinstance(price, (int, float)):
                    pricing_points.append({
                        "competitor_name": c.get("name"),
                        "price": float(price),
                        "source_url": source
                    })

        price_agr, price_contra, price_notes, price_contra_notes = cls.evaluate_pricing_agreement(pricing_points)
        claim_agr, claim_contra, claim_notes = cls.evaluate_claim_concordance(claims)

        # Entity multi-source validation: competitors cited across multiple evidence sources
        domain_mentions: Dict[str, Set[str]] = {}
        for c in competitors:
            name = (c.get("name") or "").strip().lower()
            src = cls._extract_domain(c.get("source_url") or c.get("domain") or "")
            if name and src != "unknown":
                domain_mentions.setdefault(name, set()).add(src)

        corroborated_competitors = [
            comp for comp, d_set in domain_mentions.items() if len(d_set) >= 2
        ]
        competitor_agreement_count = len(corroborated_competitors)

        total_agreements = price_agr + claim_agr + competitor_agreement_count
        total_contradictions = price_contra + claim_contra

        # Calculate concordance score [0 - 100]
        # Baseline starts at 50 if sources exist, adjusted up by agreements, down by contradictions
        if not sources:
            concordance_score = 30.0
        else:
            base_score = 50.0
            bonus = min(40.0, total_agreements * 8.0)
            penalty = min(45.0, total_contradictions * 15.0)
            concordance_score = max(10.0, min(98.0, base_score + bonus - penalty))

        return {
            "concordance_score": round(concordance_score, 1),
            "total_agreements": total_agreements,
            "total_contradictions": total_contradictions,
            "pricing_agreements": price_agr,
            "claim_agreements": claim_agr,
            "corroborated_entities_count": competitor_agreement_count,
            "agreement_notes": price_notes + claim_notes,
            "contradiction_notes": price_contra_notes
        }

agreement_engine = CrossSourceAgreementEngine()
