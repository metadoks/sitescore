from types import MappingProxyType

from .sectors import Sector


def _freeze(d):
    return MappingProxyType({k: MappingProxyType(v) for k, v in d.items()})


DEMAND_SUBFEATURE_WEIGHTS = _freeze({
    Sector.COFFEE: {
        "walkable_population": 0.70,
        "target_population_density": 0.20,
        "age_target_concentration": 0.10,
    },
    Sector.RESTAURANT: {
        "walkable_population": 0.50,
        "target_population_density": 0.30,
        "age_target_concentration": 0.20,
    },
    Sector.GYM: {
        "walkable_population": 0.30,
        "target_population_density": 0.40,
        "age_target_concentration": 0.30,
    },
    Sector.BEAUTY: {
        "walkable_population": 0.20,
        "target_population_density": 0.40,
        "age_target_concentration": 0.40,
    },
})

ACCESSIBILITY_SUBFEATURE_WEIGHTS = _freeze({
    Sector.COFFEE: {
        "walkable_reach_area": 0.50,
        "transit_access": 0.30,
        "road_parking_access": 0.20,
    },
    Sector.RESTAURANT: {
        "walkable_reach_area": 0.40,
        "transit_access": 0.30,
        "road_parking_access": 0.30,
    },
    Sector.GYM: {
        "walkable_reach_area": 0.10,
        "transit_access": 0.20,
        "road_parking_access": 0.70,
    },
    Sector.BEAUTY: {
        "walkable_reach_area": 0.10,
        "transit_access": 0.20,
        "road_parking_access": 0.70,
    },
})
