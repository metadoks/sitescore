from enum import StrEnum


class Sector(StrEnum):
    COFFEE = "coffee"
    RESTAURANT = "restaurant"
    GYM = "gym"
    BEAUTY = "beauty"


class Category(StrEnum):
    DEMAND = "demand"
    COMPETITION = "competition"
    ACCESSIBILITY = "accessibility"
    ECONOMICS = "economics"
