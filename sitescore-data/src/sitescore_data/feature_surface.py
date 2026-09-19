"""Frozen V1 normalized feature-surface identities.

This lower-level module exists so schemas and validators share one canonical
feature ordering without importing each other.
"""

NORMALIZED_FEATURE_NAMES = (
    "walkable_population_score",
    "target_population_density_score",
    "age_target_concentration_score",
    "competition_opportunity_score",
    "walkable_reach_area_score",
    "transit_access_score",
    "road_parking_access_score",
    "household_income_score",
)
