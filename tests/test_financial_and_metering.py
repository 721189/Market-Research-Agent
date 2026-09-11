import pytest
import datetime
from backend.app.services.cost import cost_service, _job_usage_context
from backend.app.research.financial import FinancialEngine, FinancialInputs
from backend.app.research.validators import ResearchValidator

def test_job_wide_llm_budget():
    job_id = "test_job_wide_123"
    # Stage 1: Research Worker initializes metering
    cost_service.start_job_metering(job_id, max_llm_calls=5, max_context_tokens=1000)
    
    # Record 2 LLM calls in Stage 1
    cost_service.record_llm_usage("gemini-1.5-flash", input_tokens=100, output_tokens=50)
    cost_service.record_llm_usage("gemini-1.5-flash", input_tokens=200, output_tokens=100)
    
    ctx1 = _job_usage_context.get()
    assert ctx1["llm_calls"] == 2
    assert ctx1["total_input_tokens"] == 300
    
    # Stage 2: Analysis Worker calls start_job_metering for the same job
    cost_service.start_job_metering(job_id, max_llm_calls=5, max_context_tokens=1000)
    ctx2 = _job_usage_context.get()
    
    # Budget must remain job-wide (calls preserved at 2, not reset to 0)
    assert ctx2["llm_calls"] == 2
    assert ctx2["total_input_tokens"] == 300

def test_aggregate_billing_per_call_sum():
    job_id = "test_job_billing_456"
    cost_service.start_job_metering(job_id, max_llm_calls=10)
    
    # Call 1: gemini-1.5-flash
    cost_service.record_llm_usage("gemini-1.5-flash", input_tokens=1_000_000, output_tokens=0) # $0.075
    # Call 2: gemini-1.5-pro
    cost_service.record_llm_usage("gemini-1.5-pro", input_tokens=1_000_000, output_tokens=0)   # $1.25
    
    ctx = _job_usage_context.get()
    calls_sum = sum(c["estimated_cost"] for c in ctx["call_records"])
    assert round(calls_sum, 3) == round(0.075 + 1.25, 3)

def test_financial_assumptions_validation():
    inputs_valid = FinancialInputs(selling_price=100.0, cogs=20.0, product_type="saas")
    is_valid, warnings = FinancialEngine.validate_assumptions(inputs_valid)
    assert is_valid is True
    assert len(warnings) == 0

    inputs_invalid_price = FinancialInputs(selling_price=-10.0, cogs=20.0)
    is_valid_p, warnings_p = FinancialEngine.validate_assumptions(inputs_invalid_price)
    assert is_valid_p is False
    assert any("selling price" in w for w in warnings_p)

    inputs_negative_margin = FinancialInputs(selling_price=50.0, cogs=60.0)
    is_valid_m, warnings_m = FinancialEngine.validate_assumptions(inputs_negative_margin)
    assert any("Gross Margin Risk" in w for w in warnings_m)

def test_validator_financial_consistency():
    # Selling price $100, COGS $20, margin 80%
    is_ok = ResearchValidator.validate_financial_consistency(cogs=20.0, price=100.0, margin=80.0, contribution_margin=75.0)
    assert is_ok is True

    # Contribution margin > Gross Profit is mathematically invalid
    is_bad = ResearchValidator.validate_financial_consistency(cogs=20.0, price=100.0, margin=80.0, contribution_margin=90.0)
    assert is_bad is False
