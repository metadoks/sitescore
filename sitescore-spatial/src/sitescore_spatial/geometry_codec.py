from __future__ import annotations

import math

import shapely
from shapely.geometry.base import BaseGeometry


def canonical_wkb_v1(geometry: BaseGeometry, *, allow_empty: bool) -> tuple[BaseGeometry, bytes]:
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("unsupported geometry type; V1 accepts Polygon/MultiPolygon only")
    if shapely.has_z(geometry) or getattr(geometry, "has_m", False):
        raise ValueError("unexpected coordinate dimensionality; V1 is 2D only")
    coords = shapely.get_coordinates(geometry, include_z=False)
    for row in coords:
        for value in row:
            if not math.isfinite(float(value)):
                raise ValueError("non-finite coordinate rejected")
    if geometry.is_empty and not allow_empty:
        raise ValueError("empty boundary geometry rejected")
    if not geometry.is_empty and not geometry.is_valid:
        raise ValueError("invalid geometry rejected; canonicalization does not repair")
    normalized = shapely.normalize(geometry)
    wkb = shapely.to_wkb(
        normalized,
        hex=False,
        output_dimension=2,
        byte_order=1,
        include_srid=False,
        flavor="iso",
    )
    return normalized, wkb
