from __future__ import annotations

from copy import deepcopy

import pytest


@pytest.fixture
def valid_payloads():
    common = {
        "location": {
            "country_code": "US",
            "street": "123 Main St",
            "city": "Austin",
            "state": "TX",
            "zip_code": "78701",
        },
        "costs": {
            "monthly_rent": 5000,
            "fixed_labor": 12000,
            "fixed_overhead": 3000,
        },
    }
    payloads = {
        "coffee": {
            **deepcopy(common),
            "sector": "coffee",
            "business_inputs": {
                "target_population": 50000,
                "target_rate": 0.35,
                "capture_rate_conservative": 0.01,
                "capture_rate_base": 0.02,
                "capture_rate_optimistic": 0.03,
                "visit_frequency_per_month": 3,
                "average_ticket": 8.5,
            },
        },
        "restaurant": {
            **deepcopy(common),
            "sector": "restaurant",
            "business_inputs": {
                "seats": 60,
                "turnover_per_day": 2.0,
                "utilization_conservative": 0.45,
                "utilization_base": 0.6,
                "utilization_optimistic": 0.75,
                "average_ticket": 32.0,
                "operating_days_per_month": 26,
            },
        },
        "gym": {
            **deepcopy(common),
            "sector": "gym",
            "business_inputs": {
                "target_population": 80000,
                "penetration_rate_conservative": 0.01,
                "penetration_rate_base": 0.02,
                "penetration_rate_optimistic": 0.03,
                "usable_area": 9000,
                "members_per_area_unit": 0.12,
                "monthly_membership_fee": 55.0,
            },
        },
        "beauty": {
            **deepcopy(common),
            "sector": "beauty",
            "business_inputs": {
                "stations": 6,
                "operating_hours_per_week": 55,
                "average_service_duration_hours": 1.25,
                "utilization_conservative": 0.45,
                "utilization_base": 0.6,
                "utilization_optimistic": 0.75,
                "average_ticket": 70.0,
            },
        },
    }
    return payloads
