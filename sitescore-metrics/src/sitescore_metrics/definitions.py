from .contracts import MetricDefinition, MetricDerivationPolicy, MeasurementPrecisionPolicy
from .enums import MetricImplementationStatus as S, DerivationStrategy as D

FULL_BINARY64 = MeasurementPrecisionPolicy("real_unit_full_binary64","1.0")

DEFINITIONS = {
 "walkable_population": MetricDefinition("walkable_population","1.0","people",S.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED),
 "target_population_density": MetricDefinition("target_population_density","1.0","people_per_km2",S.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED),
 "household_income": MetricDefinition("household_income","1.0","usd_per_household",S.PASS_THROUGH_PROVIDER_DERIVED),
 "household_income_ratio": MetricDefinition("household_income_ratio","1.0","ratio",S.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED),
 "competition_pressure": MetricDefinition("competition_pressure","1.0","competition_pressure",S.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED),
 "walkable_reach_area_km2": MetricDefinition("walkable_reach_area_km2","1.0","km2",S.PASS_THROUGH_PROVIDER_DERIVED),
 "transit_service_departure_equivalents_per_hour": MetricDefinition("transit_service_departure_equivalents_per_hour","1.0","departure_equivalents_per_hour",S.PASS_THROUGH_PROVIDER_DERIVED),
 "road_reachable_area_km2": MetricDefinition("road_reachable_area_km2","1.0","km2",S.STRUCTURALLY_SUPPORTED_BUT_POLICY_UNRESOLVED),
 "parking_public_offstreet_capacity": MetricDefinition("parking_public_offstreet_capacity","1.0","spaces",S.PASS_THROUGH_PROVIDER_DERIVED),
 "parking_legal_curb_length_m": MetricDefinition("parking_legal_curb_length_m","1.0","m",S.PASS_THROUGH_PROVIDER_DERIVED),
}
POLICIES = {
 "walkable_population": MetricDerivationPolicy("walkable_population_allocation","1.0","walkable_population",D.UNRESOLVED_ALLOCATION),
 "target_population_density": MetricDerivationPolicy("target_population_definition","1.0","target_population_density",D.UNRESOLVED_TARGET_DEFINITION),
 "household_income": MetricDerivationPolicy("household_income_passthrough","1.0","household_income",D.PASS_THROUGH_PROVIDER_DERIVED),
 "household_income_ratio": MetricDerivationPolicy("household_income_denominator","1.0","household_income_ratio",D.UNRESOLVED_DENOMINATOR),
 "competition_pressure": MetricDerivationPolicy("competition_scalar_reduction","1.0","competition_pressure",D.UNRESOLVED_REDUCTION),
 "walkable_reach_area_km2": MetricDerivationPolicy("isochrone_area_passthrough","1.0","walkable_reach_area_km2",D.PASS_THROUGH_PROVIDER_DERIVED),
 "transit_service_departure_equivalents_per_hour": MetricDerivationPolicy("transit_supply_passthrough","1.0","transit_service_departure_equivalents_per_hour",D.PASS_THROUGH_PROVIDER_DERIVED),
 "road_reachable_area_km2": MetricDerivationPolicy("road_scalar_reduction","1.0","road_reachable_area_km2",D.UNRESOLVED_REDUCTION),
 "parking_public_offstreet_capacity": MetricDerivationPolicy("parking_capacity_passthrough","1.0","parking_public_offstreet_capacity",D.PASS_THROUGH_PROVIDER_DERIVED),
 "parking_legal_curb_length_m": MetricDerivationPolicy("parking_curb_length_passthrough","1.0","parking_legal_curb_length_m",D.PASS_THROUGH_PROVIDER_DERIVED),
}
