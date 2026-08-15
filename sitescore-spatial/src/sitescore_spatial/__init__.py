from .canonicalization import canonicalize_geometry, geometry_from_canonical, operation_output_canonicalization_policy
from .compatibility import evaluate_geography_geometry_compatibility
from .contracts import *
from .crs import build_crs_identity, build_transform_plan
from .enums import *
from .geometry import build_boundary_geometry_artifact
from .hashing import HASH_ALGORITHM, SPATIAL_IDENTITY_GRAMMAR, SPATIAL_IDENTITY_GRAMMAR_VERSION, canonical_json_bytes, content_hash, semantic_hash
from .identity import build_geometry_engine_identity, build_geometry_source_identity
from .operations import area_of_projected_geometry, intersect_geometries, project_geometry

__version__ = "0.1.0"
