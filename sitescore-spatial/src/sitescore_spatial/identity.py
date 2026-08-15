from __future__ import annotations

import hashlib
import pathlib
import platform

import pyproj
import shapely

from .contracts import GeometryEngineIdentity, GeometrySourceIdentity
from .hashing import content_hash, semantic_hash
from .validation import canonical_string, immutable_release, sha256_hex


def build_geometry_source_identity(
    *,
    provider: str,
    dataset: str,
    release: str,
    vintage: str,
    schema_version: str,
    source_crs_identity,
    raw_content: bytes,
    declared_raw_content_hash: str | None = None,
) -> GeometrySourceIdentity:
    provider = canonical_string(provider, "provider")
    dataset = canonical_string(dataset, "dataset")
    release = immutable_release(release)
    vintage = immutable_release(vintage, "vintage")
    schema_version = canonical_string(schema_version, "schema_version")
    actual_hash = content_hash(raw_content)
    if declared_raw_content_hash is not None:
        sha256_hex(declared_raw_content_hash, "declared_raw_content_hash")
        if declared_raw_content_hash != actual_hash:
            raise ValueError("raw content hash mismatch")
    record = {
        "provider": provider,
        "dataset": dataset,
        "release": release,
        "vintage": vintage,
        "schema_version": schema_version,
        "source_crs_identity_id": source_crs_identity.crs_identity_id,
        "raw_content_hash": actual_hash,
    }
    return GeometrySourceIdentity(
        source_identity_id=semantic_hash(record),
        provider=provider,
        dataset=dataset,
        release=release,
        vintage=vintage,
        schema_version=schema_version,
        source_crs_identity=source_crs_identity,
        raw_content_hash=actual_hash,
    )


def _sha256_file(path: pathlib.Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_geometry_engine_identity() -> GeometryEngineIdentity:
    data_dir = pathlib.Path(pyproj.datadir.get_data_dir())
    proj_db_hash = _sha256_file(data_dir / "proj.db")
    record = {
        "python_version": platform.python_version(),
        "geometry_library": "Shapely",
        "geometry_library_version": shapely.__version__,
        "geos_version": shapely.geos_version_string,
        "projection_library": "pyproj",
        "projection_library_version": pyproj.__version__,
        "proj_version": pyproj.proj_version_str,
        "proj_database_hash": proj_db_hash,
        "engine_identity_version": "1.0",
    }
    return GeometryEngineIdentity(engine_identity_id=semantic_hash(record), **record)


def attest_actual_geometry_engine(engine: GeometryEngineIdentity) -> GeometryEngineIdentity:
    """Verify that a claimed engine record equals the active installed runtime."""
    actual = build_geometry_engine_identity()
    if engine != actual:
        raise ValueError("supplied GeometryEngineIdentity does not attest the active spatial runtime")
    return actual
