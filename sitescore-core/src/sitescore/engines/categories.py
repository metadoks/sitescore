def weighted_score(features: dict[str, float], weights: dict[str, float]) -> float:
    if set(features) != set(weights):
        missing = set(weights) - set(features)
        extra = set(features) - set(weights)
        raise ValueError(f"feature/weight mismatch; missing={missing}, extra={extra}")
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1.0")
    for name, value in features.items():
        if not 0.0 <= float(value) <= 100.0:
            raise ValueError(f"{name} must be in [0, 100]")
    return sum(float(features[name]) * float(weights[name]) for name in weights)
