from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class FinancialInputs:
    selling_price: float
    cogs: float
    monthly_fixed_costs: float = 5000.0
    customer_acquisition_cost: float = 15.0
    monthly_churn_rate_pct: float = 5.0 # Standard 5% SaaS/Subscription baseline

@dataclass
class FinancialResult:
    selling_price: float
    cogs: float
    gross_profit: float
    gross_margin_percentage: float
    markup_percentage: float
    contribution_margin_per_unit: float
    break_even_units_monthly: int
    lifetime_value_usd: float
    ltv_to_cac_ratio: float
    unit_health_status: str
    cac_payback_months: float

class FinancialEngine:
    @staticmethod
    def calculate(inputs: FinancialInputs) -> FinancialResult:
        # Strict validation
        if inputs.selling_price <= 0:
            raise ValueError("Selling price must be greater than 0")
        if inputs.cogs < 0:
            raise ValueError("COGS must be non-negative")
        
        # Gross profit & margin
        if inputs.cogs >= inputs.selling_price:
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
        safe_cac = max(0.0, inputs.customer_acquisition_cost)
        contribution_margin = gross_profit - safe_cac
        if contribution_margin > 0:
            break_even_units = int(inputs.monthly_fixed_costs / contribution_margin) + 1
        else:
            break_even_units = 999999

        # LTV and Unit Economics
        safe_churn = max(0.01, min(1.0, inputs.monthly_churn_rate_pct / 100.0))
        monthly_gp_per_user = gross_profit
        ltv = monthly_gp_per_user / safe_churn

        if safe_cac > 0:
            ltv_cac = round(ltv / safe_cac, 2)
            payback_months = round(safe_cac / max(0.01, contribution_margin), 1) if contribution_margin > 0 else 999.0
        else:
            ltv_cac = 99.0
            payback_months = 0.0

        # Qualitative health status
        if ltv_cac >= 4.0:
            health = "EXCELLENT"
        elif ltv_cac >= 3.0:
            health = "HEALTHY"
        elif ltv_cac >= 1.5:
            health = "MODERATE_RISK"
        else:
            health = "DISTRESSED"

        return FinancialResult(
            selling_price=round(inputs.selling_price, 2),
            cogs=round(inputs.cogs, 2),
            gross_profit=round(gross_profit, 2),
            gross_margin_percentage=round(gross_margin_pct, 1),
            markup_percentage=round(markup_pct, 1),
            contribution_margin_per_unit=round(contribution_margin, 2),
            break_even_units_monthly=break_even_units,
            lifetime_value_usd=round(ltv, 2),
            ltv_to_cac_ratio=ltv_cac,
            unit_health_status=health,
            cac_payback_months=payback_months
        )

    @classmethod
    def generate_scenarios(cls, base_price: float, base_cogs: float) -> Dict[str, Any]:
        """
        Calculates deterministic Best-Case, Base-Case, Worst-Case scenarios
        along with an explicit 5x5 pricing sensitivity matrix.
        """
        # Base Case
        base = cls.calculate(FinancialInputs(selling_price=base_price, cogs=base_cogs))
        
        # Best Case (+20% price, -15% COGS due to economies of scale)
        best = cls.calculate(FinancialInputs(
            selling_price=round(base_price * 1.20, 2),
            cogs=round(base_cogs * 0.85, 2),
            customer_acquisition_cost=10.0,
            monthly_churn_rate_pct=4.0
        ))
        
        # Worst Case (-15% price due to price war, +15% COGS supply chain pressure)
        worst = cls.calculate(FinancialInputs(
            selling_price=round(base_price * 0.85, 2),
            cogs=round(base_cogs * 1.15, 2),
            customer_acquisition_cost=25.0,
            monthly_churn_rate_pct=8.0
        ))

        # Sensitivity Matrix: Price variations [-20%, -10%, 0%, +10%, +20%]
        sensitivity_matrix = []
        for p_delta in [-0.20, -0.10, 0.0, 0.10, 0.20]:
            p = round(base_price * (1.0 + p_delta), 2)
            row = {
                "price_shift_pct": int(p_delta * 100),
                "selling_price": p,
                "variations": []
            }
            for c_delta in [0.20, 0.0, -0.20]:
                c = round(base_cogs * (1.0 + c_delta), 2)
                sim = cls.calculate(FinancialInputs(selling_price=p, cogs=c))
                row["variations"].append({
                    "cogs_shift_pct": int(c_delta * 100),
                    "cogs": c,
                    "gross_margin_pct": sim.gross_margin_percentage,
                    "break_even_units": sim.break_even_units_monthly
                })
            sensitivity_matrix.append(row)

        return {
            "base_case": base.__dict__,
            "best_case": best.__dict__,
            "worst_case": worst.__dict__,
            "assumptions": {
                "monthly_fixed_costs_usd": 5000.0,
                "baseline_cac_usd": 15.0,
                "monthly_churn_rate_pct": 5.0,
                "working_capital_buffer_days": 60
            },
            "sensitivity_matrix": sensitivity_matrix
        }

financial_engine = FinancialEngine()
