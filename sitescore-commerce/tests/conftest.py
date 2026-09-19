from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def valid_analysis(sector: str) -> dict:
    location = {"country_code": "US", "street": "1 Main St", "city": "Boston", "state": "MA"}
    costs = {"monthly_rent": 5000, "fixed_labor": 12000, "fixed_overhead": 2500}
    if sector == "coffee": business = {"target_population": 10000, "target_rate": 0.5, "capture_rate_conservative": 0.01, "capture_rate_base": 0.02, "capture_rate_optimistic": 0.03, "visit_frequency_per_month": 3, "average_ticket": 8}
    elif sector == "restaurant": business = {"seats": 60, "turnover_per_day": 2.0, "utilization_conservative": 0.4, "utilization_base": 0.6, "utilization_optimistic": 0.8, "average_ticket": 30, "operating_days_per_month": 26}
    elif sector == "gym": business = {"target_population": 30000, "penetration_rate_conservative": 0.01, "penetration_rate_base": 0.02, "penetration_rate_optimistic": 0.03, "usable_area": 10000, "members_per_area_unit": 0.08, "monthly_membership_fee": 55}
    else: business = {"stations": 5, "operating_hours_per_week": 45, "average_service_duration_hours": 1.0, "utilization_conservative": 0.4, "utilization_base": 0.6, "utilization_optimistic": 0.8, "average_ticket": 65}
    return {"sector": sector, "location": location, "business_inputs": business, "costs": costs}


def valid_order(sector: str = "coffee") -> dict:
    return {"product_code": "location_report_v1", "customer_email": "Customer@Example.COM", "analysis_request": valid_analysis(sector)}
