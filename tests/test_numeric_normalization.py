import pytest
from backend.app.research.claims import normalize_numeric_value, extract_claim_scope

def test_numeric_normalization_billion_usd():
    val1, dim1 = normalize_numeric_value("1.2B USD", unit="USD")
    val2, dim2 = normalize_numeric_value("1,200,000,000 USD", unit="USD")
    assert val1 == 1_200_000_000.0
    assert val2 == 1_200_000_000.0
    assert val1 == val2
    assert dim1 == "currency"
    assert dim2 == "currency"

def test_numeric_normalization_percentages():
    val1, dim1 = normalize_numeric_value("-5.2%", unit="%")
    val2, dim2 = normalize_numeric_value("24.5%", unit="%")
    assert val1 == -5.2
    assert val2 == 24.5
    assert dim1 == "percentage"
    assert dim2 == "percentage"

def test_numeric_normalization_million():
    val, dim = normalize_numeric_value("1.2M")
    assert val == 1_200_000.0

def test_numeric_normalization_euro_million():
    val, dim = normalize_numeric_value("€4.5M", unit="EUR")
    assert val == 4_500_000.0
    assert dim == "currency"

def test_scope_extraction_time_period():
    claim_2024 = {
        "claim_text": "Market size estimated at $1.2B in 2024",
        "verbatim_quote": "$1.2B in 2024",
        "unit": "USD"
    }
    claim_2025 = {
        "claim_text": "Market size projected at $1.8B in 2025",
        "verbatim_quote": "$1.8B in 2025",
        "unit": "USD"
    }
    time1, geo1 = extract_claim_scope(claim_2024)
    time2, geo2 = extract_claim_scope(claim_2025)
    assert time1 == "2024"
    assert time2 == "2025"
    assert time1 != time2

def test_scope_extraction_geography():
    claim_us = {
        "claim_text": "US domestic market size is $1.2B",
        "verbatim_quote": "US domestic $1.2B",
        "unit": "USD"
    }
    claim_global = {
        "claim_text": "Worldwide global market size is $5.0B",
        "verbatim_quote": "worldwide global market",
        "unit": "USD"
    }
    time1, geo1 = extract_claim_scope(claim_us)
    time2, geo2 = extract_claim_scope(claim_global)
    assert geo1 == "us"
    assert geo2 == "global"
    assert geo1 != geo2
