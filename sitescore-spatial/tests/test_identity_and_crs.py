import pytest

from sitescore_spatial import build_crs_identity, build_geometry_engine_identity, build_geometry_source_identity


def test_epsg_label_variants_same_crs_identity():
    assert build_crs_identity("EPSG:4326").crs_identity_id == build_crs_identity(4326).crs_identity_id


def test_crs_change_changes_identity():
    assert build_crs_identity(4326).crs_identity_id != build_crs_identity(3857).crs_identity_id


def test_crs_binds_axis_semantics():
    crs = build_crs_identity(4326)
    assert len(crs.axis_semantics) == 2
    assert crs.is_geographic and not crs.is_projected


def test_engine_records_native_versions(engine):
    assert engine.geometry_library == "Shapely"
    assert engine.geos_version
    assert engine.projection_library == "pyproj"
    assert engine.proj_version
    assert engine.proj_database_hash is not None


def test_source_storage_locator_not_part_of_identity(crs4326):
    a = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    b = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    assert a.source_identity_id == b.source_identity_id


def test_source_release_change_changes_identity(crs4326):
    a = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    b = build_geometry_source_identity(provider="p", dataset="d", release="2026.2", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    assert a.source_identity_id != b.source_identity_id


def test_source_vintage_change_changes_identity(crs4326):
    a = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    b = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2024", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    assert a.source_identity_id != b.source_identity_id


@pytest.mark.parametrize("release", ["latest", "current", "live", "release-latest", "2026/current"])
def test_mutable_release_rejected(crs4326, release):
    with pytest.raises(ValueError):
        build_geometry_source_identity(provider="p", dataset="d", release=release, vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")


def test_raw_hash_mismatch_rejected(crs4326):
    with pytest.raises(ValueError, match="raw content hash mismatch"):
        build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x", declared_raw_content_hash="0" * 64)


def test_source_crs_change_changes_source_identity(crs4326, crs3857):
    a = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    b = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs3857, raw_content=b"x")
    assert a.source_identity_id != b.source_identity_id


def test_raw_content_change_changes_source_identity(crs4326):
    a = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"x")
    b = build_geometry_source_identity(provider="p", dataset="d", release="2026.1", vintage="2025", schema_version="1", source_crs_identity=crs4326, raw_content=b"y")
    assert a.source_identity_id != b.source_identity_id
