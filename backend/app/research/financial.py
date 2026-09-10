from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class FinancialInputs:
    selling_price: float
    cogs: float
    monthly_fixed_costs: float = 5000.0
    customer_acquisition_cost: float = 15.0

@dataclass
class FinancialResult:
    selling_price: float
    cogs: float
    gross_profit: float
    gross_margin_percentage: float
    markup_percentage: float
    contribution_margin_per_unit: float
    break_even_units_monthly: int

class FinancialEngine:
    @staticmethod
    def calculate(inputs: FinancialInputs) -> FinancialResult:
        # Strict validation (Phase 8)
        if inputs.selling_price <= 0:
            raise ValueError("Selling price must be greater than 0")
        if inputs.cogs < 0:
            raise ValueError("COGS must be non-negative")
        if inputs.cogs >= inputs.selling_price:
            # Floor gross margin to 0% if COGS exceeds price
            gross_profit = max(0.0, inputs.selling_price - inputs.cogs)
            gross_margin_pct = 0.0
            markup_pct = 0.0
        else:
            gross_profit = inputs.selling_price - inputs.cogs
            gross_margin_pct = (gross_profit / inputs.selling_price) * 100.0
            markup_pct = (gross_profit / inputs.cogs * 100.0) if inputs.cogs > 0 else 100.0

        # Enforce bounds
        gross_margin_pct = min(100.0, max(0.0, gross_margin_pct))

        # Contribution margin
        contribution_margin = gross_profit - inputs.customer_acquisition_cost
        if contribution_margin > 0:
            break_even_units = int(inputs.monthly_fixed_costs / contribution_margin) + 1
        else:
            break_even_units = 999999

        return FinancialResult(
            selling_price=round(inputs.selling_price, 2),
            cogs=round(inputs.cogs, 2),
            gross_profit=round(gross_profit, 2),
            gross_margin_percentage=round(gross_margin_pct, 1),
            markup_percentage=round(markup_pct, 1),
            contribution_margin_per_unit=round(contribution_margin, 2),
            break_even_units_monthly=break_even_units
        )

    @classmethod
    def generate_scenarios(cls, base_price: float, base_cogs: float) -> Dict[str, Dict[str, Any]]:
        """
        Calculates deterministic Best-Case, Base-Case, and Worst-Case scenarios.
        """
        # Base Case
        base = cls.calculate(FinancialInputs(selling_price=base_price, cogs=base_cogs))
        
        # Best Case (+20% price, -15% COGS due to economies of scale)
        best = cls.calculate(FinancialInputs(
            selling_price=round(base_price * 1.20, 2),
            cogs=round(base_cogs * 0.85, 2),
            customer_acquisition_cost=10.0
        ))
        
        # Worst Case (-15% price due to price war, +15% COGS supply chain pressure)
        worst = cls.calculate(FinancialInputs(
            selling_price=round(base_price * 0.85, 2),
            cogs=round(base_cogs * 1.15, 2),
            customer_acquisition_cost=25.0
        ))

        return {
            "base_case": base.__dict__,
            "best_case": best.__dict__,
            "worst_case": worst.__dict__,
        }

financial_engine = FinancialEngine()
