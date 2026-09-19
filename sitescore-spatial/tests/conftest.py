from __future__ import annotations

from datetime import datetime, timezone

import pytest
from shapely.geometry import MultiPolygon, Polygon

from sitescore_spatial import (
    GeographyIdentity,
    GeometryCanonicalizationPolicy,
    GeometryOperation,
    GeometryOperationPolicy,
    build_crs_identity,
    build_geometry_engine_identity,
    build_geometry_source_identity,
    canonicalize_geometry,
)


@pytest.fixture(scope="session")
def engine():
    return build_geometry_engine_identity()


@pytest.fixture(scope="session")
def crs4326():
    return build_crs_identity("EPSG:4326")


@pytest.fixture(scope="session")
def crs3857():
    return build_crs_identity("EPSG:3857")


@pytest.fixture(scope="session")
def canon_policy():
    return GeometryCanonicalizationPolicy()


@pytest.fixture
def polygon():
    return Polygon([(29.0, 40.9), (29.1, 40.9), (29.1, 41.0), (29.0, 41.0), (29.0, 40.9)])


@pytest.fixture
def source(crs4326):
    return build_geometry_source_identity(
        provider="example-provider", dataset="boundary-dataset", release="2026-01-01", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"raw-boundary-bytes"
    )


@pytest.fixture
def geography():
    return GeographyIdentity("BLOCK_GROUP", "360610001001", "acs-2024-bg-definition")


@pytest.fixture
def canonical(polygon, crs4326, canon_policy, engine):
    return canonicalize_geometry(polygon, crs_identity=crs4326, policy=canon_policy, engine=engine)


def op_policy(operation, precision_policy, *, allow_empty=False, version="1.0"):
    return GeometryOperationPolicy(
        policy_id=f"{operation.value.lower()}-policy",
        policy_version=version,
        operation=operation,
        precision_policy=precision_policy,
        allow_empty_result=allow_empty,
    )


@pytest.fixture
def now():
    return datetime(2026, 8, 14, 7, 0, tzinfo=timezone.utc)
