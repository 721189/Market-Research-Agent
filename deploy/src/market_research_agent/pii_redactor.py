"""PII redaction utilities.

Redacts common personally-identifiable information (email addresses,
phone numbers, and US SSNs) before text is stored in logs, caches, or
audit trails so sensitive data never lands on disk or in observability
systems.
"""

import re

# Email addresses, e.g. jane.doe+tag@example.co.uk
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)
# US phone numbers: 10 digits with optional separators/area-code grouping.
_PHONE_PATTERN = re.compile(
    r"\b\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"
)
# US Social Security numbers: 123-45-6789
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_pii(text: str) -> str:
    """Replace emails, phone numbers, and SSNs with placeholders.

    Args:
        text: Arbitrary string that may contain PII.

    Returns:
        The input with PII substituted by ``[EMAIL]``, ``[PHONE]`` and
        ``[SSN]`` markers.
    """
    if not text:
        return text
    text = _EMAIL_PATTERN.sub("[EMAIL]", text)
    text = _PHONE_PATTERN.sub("[PHONE]", text)
    text = _SSN_PATTERN.sub("[SSN]", text)
    return text