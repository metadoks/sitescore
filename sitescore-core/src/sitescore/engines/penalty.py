def calculate_penalty(score: float, threshold: float, max_penalty: float) -> float:
    score = float(score)
    threshold = float(threshold)
    max_penalty = float(max_penalty)

    if not 0.0 <= score <= 100.0:
        raise ValueError("score must be in [0, 100]")
    if threshold < 0.0:
        raise ValueError("threshold cannot be negative")
    if not 0.0 <= max_penalty <= 1.0:
        raise ValueError("max_penalty must be in [0, 1]")

    if threshold == 0.0 or score >= threshold:
        return 1.0

    deficit_ratio = (threshold - score) / threshold
    return 1.0 - max_penalty * (deficit_ratio ** 2)
