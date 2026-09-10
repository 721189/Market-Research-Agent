import hashlib
from typing import List, Dict, Any
from urllib.parse import urlparse
import datetime

# High authority domain lookup
AUTHORITY_DOMAINS: Dict[str, int] = {
    "bloomberg.com": 95,
    "reuters.com": 95,
    "wsj.com": 95,
    "ft.com": 94,
    "sec.gov": 98,
    "gartner.com": 90,
    "forbes.com": 88,
    "techcrunch.com": 87,
    "statista.com": 89,
    "github.com": 85,
    "g2.com": 84,
}

class EvidenceCollector:
    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_authority(url: str) -> int:
        try:
            domain = urlparse(url).netloc.lower()
            # Strip subdomains
            parts = domain.split(".")
            if len(parts) >= 2:
                root_domain = ".".join(parts[-2:])
            else:
                root_domain = domain

            if root_domain in AUTHORITY_DOMAINS:
                return AUTHORITY_DOMAINS[root_domain]
            if domain.endswith(".gov") or domain.endswith(".edu"):
                return 92
            if domain.endswith(".org"):
                return 75
            return 60
        except Exception:
            return 50

    @staticmethod
    def compute_freshness(retrieved_at: datetime.datetime, published_at: datetime.datetime = None) -> int:
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
