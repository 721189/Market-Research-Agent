import hashlib
from typing import List, Dict, Any, Optional, Tuple, Union
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import datetime
from email.utils import parsedate_to_datetime
import re
import logging
from backend.app.services.ssrf import ssrf_protector

logger = logging.getLogger("marketai.research.evidence")

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
    "gclid", "fbclid", "msclkid", "ref", "source", "mc_cid", "mc_eid",
    "_hsenc", "_hsmi", "zanpid"
}

# Regexes for timestamp discovery in HTML content
DATE_META_PATTERNS = [
    re.compile(r'<meta[^>]+(?:property|name)=["\'](?:article:published_time|article:modified_time|og:updated_time|pubdate|date)["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:article:published_time|article:modified_time|og:updated_time|pubdate|date)["\']', re.IGNORECASE),
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'"dateModified"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)["\']', re.IGNORECASE),
]

class EvidenceCollector:
    @staticmethod
    def is_safe_public_url(url: str) -> bool:
        """
        Validates whether a URL target points to a safe public HTTP/HTTPS endpoint.
        Rejects loopback, private IPv4/IPv6, cloud metadata, and dangerous schemes.
        """
        try:
            is_valid, _, _ = ssrf_protector.validate_url(url)
            return is_valid
        except Exception:
            return False

    @staticmethod
    def sanitize_text_content(text: str, max_length: int = 500 * 1024) -> str:
        """
        Sanitizes text content against HTML injections, malicious scripts,
        event handlers, javascript pseudo-protocols, and caps max length.
        """
        if not text:
            return ""
        if len(text) > max_length:
            text = text[:max_length]
        # Remove dangerous HTML and script/style/svg blocks
        cleaned = re.sub(r'<(script|style|svg|iframe|embed|object)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'on\w+\s*=', '', cleaned, flags=re.IGNORECASE)
        # Collapse excessive whitespace
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        return cleaned.strip()

    @staticmethod
    def canonicalize_url(raw_url: str) -> Optional[str]:
        """
        Cleans and canonicalizes a URL:
        - Strips tracking query parameters
        - Strips URL fragments
        - Lowercases scheme and netloc
        - Rejects local or non-routable targets via SSRF validation
        """
        try:
            is_valid, validated_url, _ = ssrf_protector.validate_url(raw_url)
            if not is_valid or not validated_url:
                return None

            parsed = urlparse(validated_url)
            # Filter tracking query parameters
            filtered_query = [
                (k, v) for k, v in parse_qsl(parsed.query)
                if k.lower() not in TRACKING_PARAMS
            ]
            clean_query = urlencode(filtered_query)

            # Strip trailing slash from path
            path = parsed.path.rstrip("/")

            canonical = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                "", # params
                clean_query,
                ""  # fragment
            ))
            return canonical
        except Exception as e:
            logger.debug(f"Failed to canonicalize URL '{raw_url}': {e}")
            return None

    @staticmethod
    def normalize_content(raw_text: str) -> str:
        """
        Normalizes extracted text content by removing HTML script/style tags,
        collapsing excessive whitespace, and standardizing line breaks.
        """
        if not raw_text:
            return ""
        # Strip script and style blocks
        cleaned = re.sub(r'<(script|style|svg)[^>]*>.*?</\1>', '', raw_text, flags=re.DOTALL | re.IGNORECASE)
        # Strip HTML tags
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @classmethod
    def compute_hash(cls, content: Union[str, bytes]) -> str:
        """
        Computes deterministic SHA-256 content digest.
        If string content is provided, it is first normalized to guarantee stability.
        """
        if isinstance(content, str):
            normalized = cls.normalize_content(content)
            return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        elif isinstance(content, bytes):
            return hashlib.sha256(content).hexdigest()
        else:
            return hashlib.sha256(str(content).encode("utf-8")).hexdigest()

    @staticmethod
    def parse_header_date(date_str: Optional[str]) -> Optional[datetime.datetime]:
        """Parses standard HTTP RFC-2822 / RFC-1123 date strings (e.g. Last-Modified)."""
        if not date_str:
            return None
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            return None

    @classmethod
    def extract_published_date(cls, html_text: str, headers: Dict[str, str]) -> Optional[datetime.datetime]:
        """
        Extracts real published or last-modified timestamp from HTTP headers and HTML meta/JSON-LD.
        """
        # 1. Check HTTP Last-Modified header
        last_mod = headers.get("last-modified") or headers.get("date")
        dt_header = cls.parse_header_date(last_mod)
        if dt_header:
            return dt_header

        # 2. Check HTML meta tags and JSON-LD schema
        for pattern in DATE_META_PATTERNS:
            match = pattern.search(html_text)
            if match:
                raw_val = match.group(1).strip()
                try:
                    # Clean ISO format e.g. 2025-01-15T14:30:00Z
                    iso_clean = raw_val.replace("Z", "+00:00")
                    dt = datetime.datetime.fromisoformat(iso_clean)
                    return dt.replace(tzinfo=None) if dt.tzinfo else dt
                except Exception:
                    # Try YYYY-MM-DD
                    date_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})', raw_val)
                    if date_match:
                        try:
                            return datetime.datetime(
                                int(date_match.group(1)),
                                int(date_match.group(2)),
                                int(date_match.group(3))
                            )
                        except ValueError:
                            pass

        return None

    @classmethod
    def compute_freshness(cls, retrieved_at: datetime.datetime, published_at: Optional[datetime.datetime] = None) -> int:
        """
        Calculates mathematical freshness score [0-100] using real published date.
        Decay curve penalizes staleness and unverified timestamps.
        """
        if not published_at:
            # When published date cannot be extracted, apply an unverified penalty
            return 55

        now = datetime.datetime.utcnow()
        days_old = max(0, (now - published_at).days)

        if days_old <= 30:
            return 98
        elif days_old <= 90:
            return 88
        elif days_old <= 180:
            return 75
        elif days_old <= 365:
            return 60
        elif days_old <= 730:
            return 45
        else:
            return 30

    @classmethod
    async def harvest_and_hash_evidence(
        cls,
        url: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches an external source securely using SSRF protection,
        computes actual content SHA-256 hash, extracts real published date,
        and computes authority and freshness scores.
        """
        canonical_url = cls.canonicalize_url(url)
        if not canonical_url:
            return None

        try:
            status_code, raw_bytes, headers = await ssrf_protector.safe_fetch(canonical_url)
            if status_code >= 400:
                logger.warning(f"Harvest failed for '{canonical_url}': HTTP {status_code}")
                return None

            content_text = raw_bytes.decode("utf-8", errors="replace")
            content_hash = cls.compute_hash(content_text)
            published_at = cls.extract_published_date(content_text, headers)
            now = datetime.datetime.utcnow()

            authority = cls.compute_authority(canonical_url)
            freshness = cls.compute_freshness(retrieved_at=now, published_at=published_at)

            domain = urlparse(canonical_url).netloc.lower()
            return {
                "url": canonical_url,
                "domain": domain,
                "content_hash": content_hash,
                "raw_byte_size": len(raw_bytes),
                "etag": headers.get("etag"),
                "published_at": published_at.isoformat() if published_at else None,
                "retrieved_at": now.isoformat(),
                "authority_score": authority,
                "freshness_score": freshness,
                "snippet": cls.normalize_content(content_text)[:300]
            }
        except Exception as e:
            logger.warning(f"Error harvesting evidence from {url}: {e}")
            return None

    @staticmethod
    def compute_authority(url: str) -> int:
        try:
            domain = urlparse(url).netloc.lower()
            if ":" in domain:
                domain = domain.split(":")[0]

            parts = domain.split(".")
            root_domain = ".".join(parts[-2:]) if len(parts) >= 2 else domain

            if root_domain in AUTHORITY_DOMAINS:
                return AUTHORITY_DOMAINS[root_domain]
            if domain in AUTHORITY_DOMAINS:
                return AUTHORITY_DOMAINS[domain]

            if domain.endswith(".gov"):
                return 98
            if domain.endswith(".edu"):
                return 92
            if domain.endswith(".org"):
                return 78

            if root_domain in ("reddit.com", "quora.com"):
                return 45
            if root_domain in ("medium.com", "substack.com"):
                return 55

            return 65
        except Exception:
            return 50

evidence_collector = EvidenceCollector()
