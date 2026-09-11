from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class FinancialInputs:
    selling_price: float
    cogs: float
    product_type: str = "saas" # "saas" or "physical"
    monthly_fixed_costs: float = 5000.0
    customer_acquisition_cost: float = 15.0
    payment_processing_fee_pct: float = 2.9 # 2.9% + $0.30 standard Stripe fee
    payment_processing_fixed_usd: float = 0.30
    fulfillment_or_hosting_per_unit: float = 2.0
    monthly_churn_rate_pct: float = 5.0 # For subscription / SaaS
    repeat_purchase_rate_pct: float = 20.0 # For physical e-commerce

@dataclass
class FinancialResult:
    selling_price: float
    cogs: float
    variable_cost_per_unit: float
    gross_profit: float
    gross_margin_percentage: float
    markup_percentage: float
    contribution_margin_per_unit: float
    contribution_margin_ratio: float
    break_even_units_monthly: int
    break_even_revenue_monthly: float
    lifetime_value_usd: float
    ltv_to_cac_ratio: float
    unit_health_status: str
    cac_payback_months: float
    target_margin_price_70pct: float
    target_margin_price_80pct: float

class FinancialEngine:
    @staticmethod
    def calculate(inputs: FinancialInputs) -> FinancialResult:
        if inputs.selling_price <= 0:
            raise ValueError("Selling price must be greater than 0")
        if inputs.cogs < 0:
            raise ValueError("COGS must be non-negative")

        # Variable processing & fulfillment costs
        processing_fee = round((inputs.selling_price * (inputs.payment_processing_fee_pct / 100.0)) + inputs.payment_processing_fixed_usd, 2)
        total_variable_cost = round(inputs.cogs + processing_fee + inputs.fulfillment_or_hosting_per_unit, 2)

        # Gross profit & margin (Revenue - Direct COGS)
        gross_profit = round(inputs.selling_price - inputs.cogs, 2)
        gross_margin_pct = round((gross_profit / inputs.selling_price) * 100.0, 2) if inputs.selling_price > 0 else 0.0
        markup_pct = round((gross_profit / inputs.cogs * 100.0), 2) if inputs.cogs > 0 else 100.0

        # Contribution margin per unit (Revenue - Total Variable Cost)
        contribution_margin = round(inputs.selling_price - total_variable_cost, 2)
        cm_ratio = round(contribution_margin / inputs.selling_price, 4) if inputs.selling_price > 0 else 0.0

        # Break-even analysis
        if contribution_margin > 0:
            break_even_units = int(inputs.monthly_fixed_costs / contribution_margin) + 1
            break_even_revenue = round(break_even_units * inputs.selling_price, 2)
        else:
            break_even_units = 999999
            break_even_revenue = 99999999.0

        # LTV and Unit Economics
        safe_cac = max(0.01, inputs.customer_acquisition_cost)
        if inputs.product_type == "saas":
            safe_churn = max(0.01, min(1.0, inputs.monthly_churn_rate_pct / 100.0))
            ltv = round(gross_profit / safe_churn, 2)
            payback_months = round(safe_cac / max(0.01, contribution_margin), 1) if contribution_margin > 0 else 999.0
        else:
            repeat_mult = 1.0 + (inputs.repeat_purchase_rate_pct / 100.0)
            ltv = round(gross_profit * repeat_mult, 2)
            payback_months = round(safe_cac / max(0.01, contribution_margin), 1) if contribution_margin > 0 else 999.0

        ltv_cac = round(ltv / safe_cac, 2)

        # Health tier
        if ltv_cac >= 4.0 and gross_margin_pct >= 65.0:
            health = "EXCELLENT"
        elif ltv_cac >= 3.0 and gross_margin_pct >= 50.0:
            health = "HEALTHY"
        elif ltv_cac >= 1.5:
            health = "MODERATE_RISK"
        else:
            health = "DISTRESSED"

        # Target margin pricing benchmarks (Price = COGS / (1 - Target Margin))
        target_70 = round(inputs.cogs / (1.0 - 0.70), 2) if inputs.cogs > 0 else inputs.selling_price
        target_80 = round(inputs.cogs / (1.0 - 0.80), 2) if inputs.cogs > 0 else inputs.selling_price

        return FinancialResult(
            selling_price=round(inputs.selling_price, 2),
            cogs=round(inputs.cogs, 2),
            variable_cost_per_unit=total_variable_cost,
            gross_profit=gross_profit,
            gross_margin_percentage=max(0.0, min(100.0, gross_margin_pct)),
            markup_percentage=markup_pct,
            contribution_margin_per_unit=contribution_margin,
            contribution_margin_ratio=cm_ratio,
            break_even_units_monthly=break_even_units,
            break_even_revenue_monthly=break_even_revenue,
            lifetime_value_usd=ltv,
            ltv_to_cac_ratio=ltv_cac,
            unit_health_status=health,
            cac_payback_months=payback_months,
            target_margin_price_70pct=target_70,
            target_margin_price_80pct=target_80
        )

    @classmethod
    def generate_scenarios(cls, base_price: float, base_cogs: float, product_type: str = "saas") -> Dict[str, Any]:
        """Calculates Base-Case, Optimistic, and Conservative scenarios with sensitivity matrix."""
        base = cls.calculate(FinancialInputs(
            selling_price=base_price,
            cogs=base_cogs,
            product_type=product_type,
            customer_acquisition_cost=15.0
        ))
        
        optimistic = cls.calculate(FinancialInputs(
            selling_price=round(base_price * 1.15, 2),
            cogs=round(base_cogs * 0.85, 2),
            product_type=product_type,
            customer_acquisition_cost=10.0,
            monthly_churn_rate_pct=3.5
        ))
        
        conservative = cls.calculate(FinancialInputs(
            selling_price=round(base_price * 0.80, 2),
            cogs=round(base_cogs * 1.20, 2),
            product_type=product_type,
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
                sim = cls.calculate(FinancialInputs(selling_price=p, cogs=c, product_type=product_type))
                row["variations"].append({
                    "cogs_shift_pct": int(c_delta * 100),
                    "cogs": c,
                    "gross_margin_pct": sim.gross_margin_percentage,
                    "break_even_units": sim.break_even_units_monthly,
                    "contribution_margin": sim.contribution_margin_per_unit
                })
            sensitivity_matrix.append(row)

        return {
            "base_case": base.__dict__,
            "optimistic_case": optimistic.__dict__,
            "conservative_case": conservative.__dict__,
            "assumptions": {
                "monthly_fixed_costs_usd": 5000.0,
                "baseline_cac_usd": 15.0,
                "payment_fee": "2.9% + $0.30",
                "product_type": product_type
            },
            "sensitivity_matrix": sensitivity_matrix
        }

financial_engine = FinancialEngine()
