from types import MappingProxyType

CONFIDENCE_WEIGHTS = MappingProxyType({
    "geographic_precision": 0.30,
    "data_vintage": 0.20,
    "data_coverage": 0.25,
    "input_completeness": 0.25,
})

GEOGRAPHIC_PRECISION_SCORES = MappingProxyType({
    "block_group": 100.0,
    "tract": 75.0,
    "zcta": 50.0,
    "county": 25.0,
    "unknown": 0.0,
})

DATA_VINTAGE_SCORES = MappingProxyType({
    0: 100.0,
    1: 100.0,
    2: 90.0,
    3: 75.0,
    4: 55.0,
})

DATA_COVERAGE_LEVELS = MappingProxyType({
    "full": 100.0,
    "degraded": 60.0,
    "missing": 0.0,
})

INPUT_WEIGHTS = MappingProxyType({
    "rent": 0.30,
    "price": 0.30,
    "capacity": 0.25,
    "schedule": 0.15,
})

INPUT_QUALITY_SCORES = MappingProxyType({
    "user": 100.0,
    "default": 50.0,
    "missing": 0.0,
})
