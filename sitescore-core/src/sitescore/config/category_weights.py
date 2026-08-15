from types import MappingProxyType

from .sectors import Category, Sector


def _freeze(d):
    return MappingProxyType({k: MappingProxyType(v) for k, v in d.items()})


SECTOR_CATEGORY_WEIGHTS = _freeze({
    Sector.COFFEE: {
        Category.DEMAND: 0.40,
        Category.COMPETITION: 0.30,
        Category.ACCESSIBILITY: 0.20,
        Category.ECONOMICS: 0.10,
    },
    Sector.RESTAURANT: {
        Category.DEMAND: 0.25,
        Category.COMPETITION: 0.20,
        Category.ACCESSIBILITY: 0.30,
        Category.ECONOMICS: 0.25,
    },
    Sector.GYM: {
        Category.DEMAND: 0.30,
        Category.COMPETITION: 0.15,
        Category.ACCESSIBILITY: 0.30,
        Category.ECONOMICS: 0.25,
    },
    Sector.BEAUTY: {
        Category.DEMAND: 0.20,
        Category.COMPETITION: 0.25,
        Category.ACCESSIBILITY: 0.20,
        Category.ECONOMICS: 0.35,
    },
})
