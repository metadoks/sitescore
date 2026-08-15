import pytest

from sitescore.config.category_weights import SECTOR_CATEGORY_WEIGHTS
from sitescore.config.sectors import Sector
from sitescore.config.subfeature_weights import (
    ACCESSIBILITY_SUBFEATURE_WEIGHTS,
    DEMAND_SUBFEATURE_WEIGHTS,
)


def test_subfeature_weights_sum_to_one():
    for table in (DEMAND_SUBFEATURE_WEIGHTS, ACCESSIBILITY_SUBFEATURE_WEIGHTS):
        for sector in Sector:
            assert sum(table[sector].values()) == pytest.approx(1.0)


def test_category_config_is_immutable():
    with pytest.raises(TypeError):
        SECTOR_CATEGORY_WEIGHTS[Sector.COFFEE]["demand"] = 0.9
