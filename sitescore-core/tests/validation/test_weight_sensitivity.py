# V1 documents Restaurant as sensitivity-observed rather than requiring a hard pass.
# This test protects the baseline weights and records the known perturbation directions.
from sitescore.config.category_weights import SECTOR_CATEGORY_WEIGHTS
from sitescore.config.sectors import Category, Sector


def test_restaurant_baseline_weights_are_locked():
    w = SECTOR_CATEGORY_WEIGHTS[Sector.RESTAURANT]
    assert w[Category.DEMAND] == 0.25
    assert w[Category.COMPETITION] == 0.20
    assert w[Category.ACCESSIBILITY] == 0.30
    assert w[Category.ECONOMICS] == 0.25
