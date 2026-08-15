import pytest
from shapely.geometry import MultiPolygon, Point, Polygon

from sitescore_spatial import canonicalize_geometry


def test_ring_start_point_invariant(crs4326, canon_policy, engine):
    a = Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)])
    b = Polygon([(2,0),(2,2),(0,2),(0,0),(2,0)])
    ca = canonicalize_geometry(a, crs_identity=crs4326, policy=canon_policy, engine=engine)
    cb = canonicalize_geometry(b, crs_identity=crs4326, policy=canon_policy, engine=engine)
    assert ca.canonical_wkb == cb.canonical_wkb
    assert ca.semantic_geometry_id == cb.semantic_geometry_id


def test_ring_orientation_invariant(crs4326, canon_policy, engine):
    a = Polygon([(0,0),(2,0),(2,2),(0,2),(0,0)])
    b = Polygon(list(reversed([(0,0),(2,0),(2,2),(0,2),(0,0)])))
    assert canonicalize_geometry(a, crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb == canonicalize_geometry(b, crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb


def test_multipolygon_member_order_invariant(crs4326, canon_policy, engine):
    p1 = Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)])
    p2 = Polygon([(3,0),(4,0),(4,1),(3,1),(3,0)])
    a = MultiPolygon([p1,p2])
    b = MultiPolygon([p2,p1])
    assert canonicalize_geometry(a, crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb == canonicalize_geometry(b, crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb


def test_topologically_different_geometry_differs(crs4326, canon_policy, engine):
    a = Polygon([(0,0),(1,0),(1,1),(0,1),(0,0)])
    b = Polygon([(0,0),(2,0),(2,1),(0,1),(0,0)])
    assert canonicalize_geometry(a, crs_identity=crs4326, policy=canon_policy, engine=engine).semantic_geometry_id != canonicalize_geometry(b, crs_identity=crs4326, policy=canon_policy, engine=engine).semantic_geometry_id


def test_unsupported_geometry_rejected(crs4326, canon_policy, engine):
    with pytest.raises(ValueError, match="unsupported geometry"):
        canonicalize_geometry(Point(0,0), crs_identity=crs4326, policy=canon_policy, engine=engine)


def test_invalid_geometry_rejected_no_repair(crs4326, canon_policy, engine):
    bowtie = Polygon([(0,0),(2,2),(0,2),(2,0),(0,0)])
    assert not bowtie.is_valid
    with pytest.raises(ValueError, match="does not repair"):
        canonicalize_geometry(bowtie, crs_identity=crs4326, policy=canon_policy, engine=engine)


def test_empty_boundary_rejected(crs4326, canon_policy, engine):
    with pytest.raises(ValueError, match="empty boundary"):
        canonicalize_geometry(Polygon(), crs_identity=crs4326, policy=canon_policy, engine=engine)


def test_z_dimension_rejected(crs4326, canon_policy, engine):
    poly = Polygon([(0,0,1),(1,0,1),(1,1,1),(0,0,1)])
    with pytest.raises(ValueError, match="2D"):
        canonicalize_geometry(poly, crs_identity=crs4326, policy=canon_policy, engine=engine)


def test_geojson_key_order_noise_invariant(crs4326, canon_policy, engine):
    a = {"type":"Polygon", "coordinates":[[[0,0],[1,0],[1,1],[0,0]]]}
    b = {"coordinates":[[[0,0],[1,0],[1,1],[0,0]]], "type":"Polygon"}
    assert canonicalize_geometry(a, crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb == canonicalize_geometry(b, crs_identity=crs4326, policy=canon_policy, engine=engine).canonical_wkb


def test_non_finite_coordinate_rejected(crs4326, canon_policy, engine):
    import warnings
    import shapely
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        poly = shapely.from_wkt("POLYGON ((0 0, 1 0, 1 NaN, 0 0))")
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize_geometry(poly, crs_identity=crs4326, policy=canon_policy, engine=engine)
