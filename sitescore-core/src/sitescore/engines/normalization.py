def percentile_to_score(percentile: float) -> float:
    """V1 pass-through for an already computed local/metro percentile in [0, 100]."""
    percentile = float(percentile)
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be in [0, 100]")
    return percentile
