import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import datetime
import re

# Comprehensive Authority Domain Index
AUTHORITY_DOMAINS: Dict[str, int] = {
    # Regulatory & Disclosures (96-98)
    "sec.gov": 98,
    "fedreserve.gov": 97,
    "census.gov": 96,
    "bls.gov": 96,
    
    # Tier-1 Financial & Economic Journals (92-95)
    "bloomberg.com": 95,
    "reuters.com": 95,
    "wsj.com": 95,
    "ft.com": 94,
    "economist.com": 93,
    
    # Top Strategy & Market Research Analysts (88-92)
    "gartner.com": 92,
    "forrester.com": 91,
    "mckinsey.com": 92,
    "bcg.com": 91,
    "statista.com": 90,
    "pitchbook.com": 90,
    "crunchbase.com": 88,
    
    # Technology, Code & Software Intelligence (80-87)
    "techcrunch.com": 87,
    "github.com": 86,
    "g2.com": 85,
    "capterra.com": 84,
    "trustradius.com": 83,
    "producthunt.com": 80,
    "forbes.com": 85,
}

# Tracking query parameters to strip for canonical deduplication
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "ref", "source", "mc_cid", "mc_eid"
}

DISALLOWED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

class EvidenceCollector:
    @staticmethod
    def canonicalize_url(raw_url: str) -> Optional[str]:
        """
        Cleans and canonicalizes a URL:
        - Strips tracking query parameters
        - Strips URL fragments
        - Lowercases scheme and netloc
        - Rejects local or non-routable targets
        """
        try:
            parsed = urlparse(raw_url.strip())
            if parsed.scheme not in ("http", "https"):
                return None

            netloc = parsed.netloc.lower()
            if not netloc or netloc in DISALLOWED_HOSTS or netloc.startswith("192.168.") or netloc.startswith("10."):
                return None

            # Filter query params
            filtered_query = [
                (k, v) for k, v in parse_qsl(parsed.query)
                if k.lower() not in TRACKING_PARAMS
            ]
            clean_query = urlencode(filtered_query)

            # Strip trailing slash from path
            path = parsed.path.rstrip("/")
            if not path:
                path = ""

            canonical = urlunparse((
                parsed.scheme.lower(),
                netloc,
                path,
                "", # params
                clean_query,
                ""  # fragment
            ))
            return canonical
        except Exception:
            return None

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_authority(url: str) -> int:
        try:
            domain = urlparse(url).netloc.lower()
            # Strip port if present
            if ":" in domain:
                domain = domain.split(":")[0]

            # Extract root domain (e.g. news.bloomberg.com -> bloomberg.com)
            parts = domain.split(".")
            if len(parts) >= 2:
                root_domain = ".".join(parts[-2:])
            else:
                root_domain = domain

            if root_domain in AUTHORITY_DOMAINS:
                return AUTHORITY_DOMAINS[root_domain]
            if domain in AUTHORITY_DOMAINS:
                return AUTHORITY_DOMAINS[domain]

            # Top-level domain heuristics
            if domain.endswith(".gov"):
                return 95
            if domain.endswith(".edu"):
                return 92
            if domain.endswith(".org"):
                return 78

            # Penalize unverified community forums
            if root_domain in ("reddit.com", "quora.com"):
                return 45
            if root_domain in ("medium.com", "substack.com"):
                return 55

            return 65
        except Exception:
            return 50

    @staticmethod
    def compute_freshness(retrieved_at: datetime.datetime, published_at: Optional[datetime.datetime] = None) -> int:
        ref_time = published_at or retrieved_at
        days_old = (datetime.datetime.utcnow() - ref_time).days
        if days_old <= 30:
            return 95
        if days_old <= 90:
            return 85
        if days_old <= 180:
            return 70
        if days_old <= 365:
            return 55
        return 40

evidence_collector = EvidenceCollector()
