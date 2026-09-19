import pytest

from sitescore.engines.penalty import calculate_penalty


def test_t_zero_guard():
    assert calculate_penalty(0, 0, 0) == 1.0
    assert calculate_penalty(50, 0, 0.5) == 1.0


def test_at_or_above_threshold_has_no_penalty():
    assert calculate_penalty(35, 35, 0.45) == 1.0
    assert calculate_penalty(36, 35, 0.45) == 1.0


def test_zero_score_hits_max_penalty():
    assert calculate_penalty(0, 35, 0.45) == pytest.approx(0.55)


def test_half_threshold_quadratic_penalty():
    assert calculate_penalty(17.5, 35, 0.45) == pytest.approx(0.8875)


def test_invalid_inputs_rejected():
    with pytest.raises(ValueError):
        calculate_penalty(-1, 35, 0.45)
    with pytest.raises(ValueError):
        calculate_penalty(10, -1, 0.45)
    with pytest.raises(ValueError):
        calculate_penalty(10, 35, 1.1)
