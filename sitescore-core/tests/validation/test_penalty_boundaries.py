import pytest

from sitescore.config.dealbreakers import DEALBREAKERS
from sitescore.config.sectors import Sector
from sitescore.engines.penalty import calculate_penalty


def test_penalty_boundary_is_continuous_and_monotonic():
    for sector in Sector:
        for rule in DEALBREAKERS[sector].values():
            if rule.threshold == 0:
                assert calculate_penalty(0, rule.threshold, rule.max_penalty) == 1.0
                continue
            t = rule.threshold
            points = [0, t / 2, max(0, t - 1), t, min(100, t + 1)]
            penalties = [calculate_penalty(s, t, rule.max_penalty) for s in points]
            assert penalties == sorted(penalties)
            assert penalties[-1] == pytest.approx(1.0)
            assert calculate_penalty(t - 1e-6, t, rule.max_penalty) == pytest.approx(1.0, abs=1e-10)
