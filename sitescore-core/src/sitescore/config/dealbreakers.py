from dataclasses import dataclass
from types import MappingProxyType

from .sectors import Category, Sector


@dataclass(frozen=True, slots=True)
class DealbreakerRule:
    threshold: float
    max_penalty: float


def _rules(**kwargs):
    return MappingProxyType(kwargs)


DEALBREAKERS = MappingProxyType({
    Sector.COFFEE: _rules(
        demand=DealbreakerRule(35.0, 0.45),
        competition=DealbreakerRule(30.0, 0.40),
        accessibility=DealbreakerRule(30.0, 0.40),
        economics=DealbreakerRule(0.0, 0.00),
    ),
    Sector.RESTAURANT: _rules(
        demand=DealbreakerRule(30.0, 0.35),
        competition=DealbreakerRule(20.0, 0.20),
        accessibility=DealbreakerRule(25.0, 0.30),
        economics=DealbreakerRule(25.0, 0.30),
    ),
    Sector.GYM: _rules(
        demand=DealbreakerRule(25.0, 0.30),
        competition=DealbreakerRule(20.0, 0.25),
        accessibility=DealbreakerRule(30.0, 0.40),
        economics=DealbreakerRule(20.0, 0.25),
    ),
    Sector.BEAUTY: _rules(
        demand=DealbreakerRule(20.0, 0.25),
        competition=DealbreakerRule(25.0, 0.35),
        accessibility=DealbreakerRule(20.0, 0.20),
        economics=DealbreakerRule(35.0, 0.45),
    ),
})

# Ensure keys remain Category-compatible while preserving simple config readability.
def get_rule(sector: Sector, category: Category) -> DealbreakerRule:
    return DEALBREAKERS[sector][category.value]
