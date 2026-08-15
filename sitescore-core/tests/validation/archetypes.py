from sitescore.schemas.location import CategoryScores

ARCHETYPES = {
    "red_ocean": CategoryScores(95, 10, 90, 80),
    "rich_ghost_town": CategoryScores(20, 90, 30, 95),
    "transit_hub": CategoryScores(90, 60, 95, 20),
    "balanced_winner": CategoryScores(80, 75, 80, 75),
    "dead_zone": CategoryScores(10, 90, 20, 20),
    "suburban_family_hub": CategoryScores(70, 70, 45, 85),
    "college_district": CategoryScores(95, 35, 90, 35),
    "tourist_district": CategoryScores(90, 25, 90, 70),
}
