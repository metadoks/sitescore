from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyproj
from pyproj import CRS
from pyproj.transformer import TransformerGroup

from .contracts import AxisSemantic, CRSIdentity, CRSTransformPolicy, GeometryEngineIdentity, TransformPlan
from .hashing import semantic_hash
from .identity import attest_actual_geometry_engine


def _canonical_projjson_text(crs: CRS) -> str:
    return json.dumps(crs.to_json_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_crs_identity(value) -> CRSIdentity:
    crs = CRS.from_user_input(value)
    canonical_definition = _canonical_projjson_text(crs)
    definition_hash = semantic_hash(json.loads(canonical_definition))
    authority = crs.to_authority()
    if authority is not None:
        try:
            authority_crs = CRS.from_user_input(f"{authority[0]}:{authority[1]}")
            if _canonical_projjson_text(authority_crs) != canonical_definition:
                authority = None
        except Exception:
            authority = None
    axis = tuple(
        AxisSemantic(
            name=a.name,
            direction=a.direction,
            unit_name=a.unit_name,
            unit_conversion_factor=float(a.unit_conversion_factor),
        )
        for a in crs.axis_info
    )
    record = {
        "authority": authority[0] if authority else None,
        "authority_code": authority[1] if authority else None,
        "canonical_definition_hash": definition_hash,
        "axis_semantics": [a.semantic_record() for a in axis],
        "is_geographic": bool(crs.is_geographic),
        "is_projected": bool(crs.is_projected),
        "definition_policy_id": "projjson",
        "definition_policy_version": "1.0",
    }
    return CRSIdentity(
        crs_identity_id=semantic_hash(record),
        authority=record["authority"],
        authority_code=record["authority_code"],
        canonical_definition=canonical_definition,
        axis_semantics=axis,
        is_geographic=record["is_geographic"],
        is_projected=record["is_projected"],
        definition_policy_id=record["definition_policy_id"],
        definition_policy_version=record["definition_policy_version"],
    )


def _crs_from_identity(identity: CRSIdentity) -> CRS:
    """Reconstruct and attest executable CRS semantics from the identity's canonical PROJJSON."""
    if not isinstance(identity, CRSIdentity):
        raise TypeError("identity must be CRSIdentity")
    try:
        crs = CRS.from_json(identity.canonical_definition)
    except Exception as exc:
        raise ValueError("CRSIdentity canonical definition is not executable") from exc
    # CRSIdentity.__post_init__ already verifies derived semantics. Repeat authority resolution at execution
    # to ensure the active pinned runtime still resolves an authority-backed CRS to the same definition.
    if identity.authority and identity.authority_code:
        authority_crs = CRS.from_user_input(f"{identity.authority}:{identity.authority_code}")
        if _canonical_projjson_text(authority_crs) != identity.canonical_definition:
            raise ValueError("active runtime authority CRS no longer matches supplied CRSIdentity")
    if _canonical_projjson_text(crs) != identity.canonical_definition:
        raise ValueError("active runtime CRS round-trip does not match supplied CRSIdentity")
    return crs


def _grid_identities(transformer) -> tuple[tuple[str, ...], bool]:
    grids: list[str] = []
    unresolved_selected_grid = False
    try:
        search_dirs = [Path(pyproj.datadir.get_data_dir()), Path(pyproj.datadir.get_user_data_dir())]
        for operation in transformer.operations:
            for grid in getattr(operation, "grids", ()):
                short = getattr(grid, "short_name", None)
                available = bool(getattr(grid, "available", False))
                if not short:
                    continue
                grid_path = None
                full_name = getattr(grid, "full_name", None)
                if full_name and Path(full_name).is_file():
                    grid_path = Path(full_name)
                else:
                    for directory in search_dirs:
                        candidate = directory / short
                        if candidate.is_file():
                            grid_path = candidate
                            break
                if grid_path is not None:
                    digest = hashlib.sha256(grid_path.read_bytes()).hexdigest()
                    grids.append(f"{short}:sha256={digest}")
                elif available:
                    unresolved_selected_grid = True
                    grids.append(f"{short}:available=true:content_hash=unresolved")
                else:
                    grids.append(f"{short}:available=false")
    except Exception:
        return (), True
    return tuple(sorted(grids)), unresolved_selected_grid


def resolve_transform_plan(
    source: CRSIdentity,
    target: CRSIdentity,
    policy: CRSTransformPolicy,
    engine: GeometryEngineIdentity,
):
    """Resolve one TransformerGroup once and return its immutable plan plus exact runtime Transformer."""
    attest_actual_geometry_engine(engine)
    pyproj.network.set_network_enabled(False)
    if pyproj.network.is_network_enabled():
        return None, None, ("proj_network_not_disabled",)
    try:
        source_crs = _crs_from_identity(source)
        target_crs = _crs_from_identity(target)
        group = TransformerGroup(source_crs, target_crs, always_xy=True, allow_ballpark=policy.allow_ballpark)
    except Exception:
        return None, None, ("transformer_group_creation_failed",)
    if policy.require_best_available and not group.best_available:
        return None, None, ("best_transformation_unavailable",)
    if not group.transformers:
        return None, None, ("no_transformation_available",)
    transformer = group.transformers[0]
    definition = transformer.definition
    if not definition or definition == "unavailable until proj_trans is called":
        definition = transformer.description
    grids, unresolved_selected_grid = _grid_identities(transformer)
    if unresolved_selected_grid:
        return None, None, ("selected_grid_identity_unresolved",)
    selected_pipeline_hash = semantic_hash({"definition": definition, "grid_identities": list(grids)})
    record = {
        "source_crs_identity_id": source.crs_identity_id,
        "target_crs_identity_id": target.crs_identity_id,
        "policy_identity_id": policy.identity_id,
        "engine_identity_id": engine.engine_identity_id,
        "selected_pipeline_hash": selected_pipeline_hash,
        "grid_identities": list(grids),
    }
    plan = TransformPlan(
        plan_id=semantic_hash(record),
        source_crs_identity=source,
        target_crs_identity=target,
        transform_policy=policy,
        engine_identity=engine,
        selected_pipeline_hash=selected_pipeline_hash,
        selected_pipeline_definition=definition,
        grid_identities=grids,
    )
    return plan, transformer, ()


def build_transform_plan(
    source: CRSIdentity,
    target: CRSIdentity,
    policy: CRSTransformPolicy,
    engine: GeometryEngineIdentity,
) -> tuple[TransformPlan | None, tuple[str, ...]]:
    plan, _transformer, reasons = resolve_transform_plan(source, target, policy, engine)
    return plan, reasons


def transformer_from_plan(plan: TransformPlan):
    """Strict exact replay helper; never falls back to generic CRS reselection."""
    try:
        transformer = pyproj.Transformer.from_pipeline(plan.selected_pipeline_definition)
    except Exception:
        return None
    definition = transformer.definition
    if not definition or definition == "unavailable until proj_trans is called":
        definition = transformer.description
    grids, unresolved = _grid_identities(transformer)
    if unresolved:
        return None
    pipeline_hash = semantic_hash({"definition": definition, "grid_identities": list(grids)})
    if pipeline_hash != plan.selected_pipeline_hash or grids != plan.grid_identities:
        return None
    return transformer
