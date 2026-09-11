import pytest
import ipaddress
import socket
from unittest.mock import patch
from backend.app.research.evidence import evidence_collector

class TestSSRFAndNetworkSecurity:
    """Security tests validating SSRF mitigations, private IP rejection, metadata service protection, and DNS rebinding."""

    def test_localhost_and_loopback_rejected(self):
        """Verify localhost URLs and loopback IPs are identified as private and blocked."""
        disallowed_urls = [
            "http://127.0.0.1:8000/internal",
            "http://127.0.0.2:9000",
            "http://localhost:3000/metrics",
            "http://0.0.0.0:5000",
            "http://127.127.127.127",
            "https://localhost/api"
        ]
        for url in disallowed_urls:
            assert evidence_collector.is_safe_public_url(url) is False, f"URL {url} should be rejected"

    def test_private_ipv4_ranges_rejected(self):
        """Verify RFC 1918 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) are blocked."""
        private_ipv4_samples = [
            "http://10.0.0.1/admin",
            "http://10.254.254.254",
            "http://172.16.0.5:8080",
            "http://172.31.255.255",
            "http://192.168.1.1/router",
            "http://192.168.0.254",
            "http://100.64.0.1" # Carrier Grade NAT
        ]
        for url in private_ipv4_samples:
            assert evidence_collector.is_safe_public_url(url) is False, f"Private IPv4 {url} should be rejected"

    def test_cloud_metadata_service_rejected(self):
        """Verify AWS/GCP/Azure link-local metadata IP (169.254.169.254) is blocked."""
        metadata_endpoints = [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.169.254/computeMetadata/v1/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://[fd00:ec2::254]/latest/meta-data/"
        ]
        for url in metadata_endpoints:
            assert evidence_collector.is_safe_public_url(url) is False, f"Metadata service {url} should be blocked"

    def test_private_ipv6_ranges_rejected(self):
        """Verify IPv6 loopback, unique local (fc00::/7), and link-local (fe80::/10) are blocked."""
        private_ipv6_samples = [
            "http://[::1]/debug",
            "http://[fe80::1]/secrets",
            "http://[fc00::1]/admin",
            "http://[fd12:3456:789a:1::1]"
        ]
        for url in private_ipv6_samples:
            assert evidence_collector.is_safe_public_url(url) is False, f"Private IPv6 {url} should be rejected"

    def test_non_http_schemes_rejected(self):
        """Verify non-HTTP schemes (file://, gopher://, ftp://, dict://) are rejected."""
        dangerous_schemes = [
            "file:///etc/passwd",
            "gopher://127.0.0.1:70",
            "ftp://internal.repo/package",
            "dict://127.0.0.1:11211",
            "ldap://127.0.0.1:389"
        ]
        for url in dangerous_schemes:
            assert evidence_collector.is_safe_public_url(url) is False, f"Scheme in {url} should be rejected"

    def test_dns_rebinding_simulation(self):
        """Verify that hostnames resolving to private IP addresses are rejected during resolution checks."""
        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 80))]), \
             patch("socket.gethostbyname", return_value="127.0.0.1"):
            assert evidence_collector.is_safe_public_url("http://rebind-attack.com/hook") is False

        with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.10.10.10', 80))]), \
             patch("socket.gethostbyname", return_value="10.10.10.10"):
            assert evidence_collector.is_safe_public_url("http://spoofed-intranet.com") is False

    def test_valid_public_urls_accepted(self):
        """Verify legitimate public internet targets pass validation."""
        valid_urls = [
            "https://techcrunch.com/2025/01/15/ai-startups",
            "https://www.statista.com/outlook/dmo/fintech/worldwide",
            "https://gartner.com/en/newsroom",
            "https://bloomberg.com/news/articles/2025-02-10/saas-market"
        ]
        for url in valid_urls:
            with patch("socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]), \
                 patch("socket.gethostbyname", return_value="93.184.216.34"): # Example public IP
                assert evidence_collector.is_safe_public_url(url) is True, f"Legitimate public URL {url} should pass"
