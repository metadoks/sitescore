"""Strict Valhalla GeoJSON parsing and deterministic road geometry canonicalization."""

from __future__ import annotations

import math
from typing import Any

from ..errors import ProviderInvariantError, ProviderMalformedResponseError
from .client import (
    VALHALLA_PARSER_VERSION,
    ParsedValhallaResponse,
    build_isochrone_request_fingerprint,
    routing_provider_identity,
)
from sitescore_data.schemas.road import RoadOriginQuality

from .models import (
    OriginSnapState,
    RoadContourEvidence,
    RoadIsochroneEvidence,
    RoadIsochroneRequest,
    CanonicalRoadGeometry,
    RoutedOriginEvidence,
    RoadValhallaWarningEvidence,
    VALHALLA_PARSER_ID,
)


def _number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderMalformedResponseError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ProviderMalformedResponseError(f"{field} must be finite")
    return number


def _coordinate(value: object, *, field: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)) or len(value) < 2:
        raise ProviderMalformedResponseError(f"{field} must be a [longitude, latitude] coordinate")
    lon = _number(value[0], field=f"{field}.longitude")
    lat = _number(value[1], field=f"{field}.latitude")
    if not -180.0 <= lon <= 180.0 or not -90.0 <= lat <= 90.0:
        raise ProviderMalformedResponseError(f"{field} coordinate is out of bounds")
    return (lon, lat)


def _canonical_ring(value: object, *, field: str) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ProviderMalformedResponseError(f"{field} must be a coordinate sequence")
    points = tuple(_coordinate(item, field=f"{field}[{index}]") for index, item in enumerate(value))
    if len(points) < 4:
        raise ProviderMalformedResponseError(f"{field} must contain at least four positions")
    if points[0] != points[-1]:
        raise ProviderMalformedResponseError(f"{field} must be a closed linear ring")
    core = points[:-1]
    if len(set(core)) < 3:
        raise ProviderMalformedResponseError(f"{field} must contain at least three distinct positions")

    def rotations(seq: tuple[tuple[float, float], ...]):
        return tuple(seq[i:] + seq[:i] for i in range(len(seq)))

    candidates = rotations(core) + rotations(tuple(reversed(core)))
    best = min(candidates)
    return best + (best[0],)


def _canonical_polygon(value: object, *, field: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)) or not value:
        raise ProviderMalformedResponseError(f"{field} must contain polygon rings")
    rings = tuple(_canonical_ring(ring, field=f"{field}[{index}]") for index, ring in enumerate(value))
    exterior = rings[0]
    holes = tuple(sorted(rings[1:]))
    return (exterior,) + holes


def canonicalize_geometry(
    *, geometry: object, request: RoadIsochroneRequest
) -> CanonicalRoadGeometry:
    if not isinstance(geometry, dict):
        raise ProviderMalformedResponseError("feature geometry must be an object")
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        polygon = _canonical_polygon(coordinates, field="Polygon.coordinates")
        canonical: tuple[Any, ...] = polygon
    elif geometry_type == "MultiPolygon":
        if not isinstance(coordinates, (list, tuple)) or isinstance(coordinates, (str, bytes)) or not coordinates:
            raise ProviderMalformedResponseError("MultiPolygon.coordinates must contain polygons")
        polygons = tuple(
            _canonical_polygon(polygon, field=f"MultiPolygon.coordinates[{index}]")
            for index, polygon in enumerate(coordinates)
        )
        canonical = tuple(sorted(polygons))
    else:
        raise ProviderMalformedResponseError("contour geometry must be Polygon or MultiPolygon")
    return CanonicalRoadGeometry(
        geometry_type=geometry_type,
        coordinates=canonical,
        crs_id=request.geometry_policy.crs_id,
        policy_identity=request.geometry_policy.identity,
    )


def _find_scale(request: RoadIsochroneRequest, contour_minutes: float):
    seconds = contour_minutes * 60.0
    matches = [
        scale for scale in request.budget_policy.scales
        if math.isclose(float(scale.travel_cost_seconds), seconds, rel_tol=0.0, abs_tol=1e-7)
    ]
    if len(matches) != 1:
        raise ProviderInvariantError("returned contour does not match exactly one requested driveing scale")
    return matches[0]


def _parse_location_feature(geometry: dict[str, object]) -> tuple[float, float]:
    if geometry.get("type") != "MultiPoint":
        raise ProviderMalformedResponseError("show_locations feature must be a MultiPoint")
    coords = geometry.get("coordinates")
    if not isinstance(coords, (list, tuple)) or isinstance(coords, (str, bytes)) or len(coords) != 1:
        raise ProviderMalformedResponseError("each show_locations MultiPoint must contain exactly one coordinate")
    return _coordinate(coords[0], field="show_locations.coordinates[0]")


def validate_road_isochrone_evidence(evidence: RoadIsochroneEvidence) -> None:
    """Revalidate canonical request/provider/parser/geometry lineage before consumption."""
    if not isinstance(evidence, RoadIsochroneEvidence):
        raise TypeError("evidence must be a RoadIsochroneEvidence")
    expected_fingerprint = build_isochrone_request_fingerprint(evidence.request)
    if evidence.request_fingerprint != expected_fingerprint:
        raise ProviderInvariantError("evidence request fingerprint does not match active request semantics")
    if evidence.raw_artifact.request_fingerprint != expected_fingerprint:
        raise ProviderInvariantError("raw artifact request fingerprint does not match active request semantics")
    if evidence.raw_artifact.provider_identity != routing_provider_identity(evidence.request):
        raise ProviderInvariantError("raw provider identity does not match active routing manifest")
    if evidence.parsed_artifact.raw_content_hash != evidence.raw_artifact.content_hash:
        raise ProviderInvariantError("parsed/raw content lineage mismatch")
    if evidence.parsed_artifact.parser_id != VALHALLA_PARSER_ID:
        raise ProviderInvariantError("wrong Valhalla parsed artifact parser_id")
    if evidence.parsed_artifact.parser_version != VALHALLA_PARSER_VERSION:
        raise ProviderInvariantError("wrong Valhalla parsed artifact parser_version")
    if (
        evidence.routed_origin.requested_latitude != evidence.request.origin.latitude
        or evidence.routed_origin.requested_longitude != evidence.request.origin.longitude
    ):
        raise ProviderInvariantError("routed-origin evidence must bind the exact requested origin")
    expected_scales = tuple((s.scale_id, float(s.travel_cost_seconds)) for s in evidence.request.budget_policy.scales)
    actual_scales = tuple((c.scale_id, float(c.travel_cost_seconds)) for c in evidence.contours)
    if actual_scales != expected_scales:
        raise ProviderInvariantError("contour evidence must exactly match driveing budget policy")
    for contour in evidence.contours:
        if contour.geometry.policy_identity != evidence.request.geometry_policy.identity:
            raise ProviderInvariantError("contour geometry is not bound to active geometry policy")
        if contour.geometry.crs_id != evidence.request.geometry_policy.crs_id:
            raise ProviderInvariantError("contour geometry CRS does not match active geometry policy")


def parse_valhalla_isochrone_evidence(
    *,
    response: ParsedValhallaResponse,
    request: RoadIsochroneRequest,
) -> RoadIsochroneEvidence:
    if not isinstance(response, ParsedValhallaResponse):
        raise TypeError("response must be a ParsedValhallaResponse")
    if not isinstance(request, RoadIsochroneRequest):
        raise TypeError("request must be a RoadIsochroneRequest")
    expected_fingerprint = build_isochrone_request_fingerprint(request)
    if response.raw_artifact.request_fingerprint != expected_fingerprint:
        raise ProviderInvariantError("raw request fingerprint does not match active isochrone request")
    if response.raw_artifact.provider_identity != routing_provider_identity(request):
        raise ProviderInvariantError("raw provider identity does not match active routing manifest")
    if response.parsed_artifact.raw_content_hash != response.raw_artifact.content_hash:
        raise ProviderInvariantError("parsed/raw content lineage mismatch")
    if response.parsed_artifact.parser_id != VALHALLA_PARSER_ID:
        raise ProviderInvariantError("wrong Valhalla parsed artifact parser_id")
    if response.parsed_artifact.parser_version != VALHALLA_PARSER_VERSION:
        raise ProviderInvariantError("wrong Valhalla parsed artifact parser_version")

    payload = response.parsed_value
    raw_warnings = payload.get("warnings", [])
    if raw_warnings is None:
        raw_warnings = []
    if not isinstance(raw_warnings, list):
        raise ProviderMalformedResponseError("Valhalla top-level warnings must be a list when present")
    warnings = tuple(RoadValhallaWarningEvidence(warning) for warning in raw_warnings)
    if payload.get("type") != "FeatureCollection":
        raise ProviderMalformedResponseError("Valhalla isochrone response must be a GeoJSON FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ProviderMalformedResponseError("GeoJSON FeatureCollection.features must be a list")

    contours: dict[str, RoadContourEvidence] = {}
    location_points: list[tuple[float, float]] = []
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ProviderMalformedResponseError(f"features[{index}] must be a GeoJSON Feature")
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if not isinstance(geometry, dict):
            raise ProviderMalformedResponseError(f"features[{index}].geometry must be an object")
        if properties is None:
            properties = {}
        if not isinstance(properties, dict):
            raise ProviderMalformedResponseError(f"features[{index}].properties must be an object")

        geometry_type = geometry.get("type")
        if geometry_type in {"Polygon", "MultiPolygon"}:
            metric = properties.get("metric")
            if metric not in {None, "time"}:
                raise ProviderInvariantError("canonical road isochrone accepts time contours only")
            if "contour" not in properties:
                raise ProviderMalformedResponseError("contour feature is missing properties.contour")
            contour_minutes = _number(properties["contour"], field="properties.contour")
            scale = _find_scale(request, contour_minutes)
            if scale.scale_id in contours:
                raise ProviderInvariantError("duplicate contour returned for requested scale")
            contours[scale.scale_id] = RoadContourEvidence(
                scale_id=scale.scale_id,
                travel_cost_seconds=float(scale.travel_cost_seconds),
                geometry=canonicalize_geometry(geometry=geometry, request=request),
            )
        elif geometry_type == "MultiPoint":
            location_points.append(_parse_location_feature(geometry))
            if len(location_points) > 2:
                raise ProviderInvariantError("show_locations returned more than exact-input and snapped-node features")
        else:
            raise ProviderMalformedResponseError(f"unsupported GeoJSON geometry type: {geometry_type!r}")

    ordered: list[RoadContourEvidence] = []
    for scale in request.budget_policy.scales:
        contour = contours.get(scale.scale_id)
        if contour is None:
            raise ProviderInvariantError(f"missing requested contour scale: {scale.scale_id}")
        ordered.append(contour)

    requested = (float(request.origin.longitude), float(request.origin.latitude))
    if len(location_points) == 2:
        exact_indexes = [
            index for index, point in enumerate(location_points)
            if math.isclose(point[0], requested[0], rel_tol=0, abs_tol=1e-12)
            and math.isclose(point[1], requested[1], rel_tol=0, abs_tol=1e-12)
        ]
        if len(exact_indexes) == 1:
            routed_point = location_points[1 - exact_indexes[0]]
            routed_origin = RoutedOriginEvidence(
                requested_latitude=request.origin.latitude,
                requested_longitude=request.origin.longitude,
                snap_state=OriginSnapState.RESOLVED,
                routed_latitude=routed_point[1],
                routed_longitude=routed_point[0],
                road_origin_quality=RoadOriginQuality.ROAD_SEGMENT_FALLBACK,
            )
        elif len(exact_indexes) == 2:
            # Numerically identical points do not expose which occurrence is the
            # snapped-node role. Do not fabricate roles from feature ordering.
            routed_origin = RoutedOriginEvidence(
                requested_latitude=request.origin.latitude,
                requested_longitude=request.origin.longitude,
                snap_state=OriginSnapState.UNKNOWN,
                routed_latitude=None,
                routed_longitude=None,
                road_origin_quality=RoadOriginQuality.UNRESOLVED,
            )
        else:
            raise ProviderInvariantError("show_locations did not return the exact requested input coordinate")
    elif location_points:
        # Partial show_locations output cannot establish a snap; preserve UNKNOWN.
        routed_origin = RoutedOriginEvidence(
            requested_latitude=request.origin.latitude,
            requested_longitude=request.origin.longitude,
            snap_state=OriginSnapState.UNKNOWN,
            routed_latitude=None,
            routed_longitude=None,
            road_origin_quality=RoadOriginQuality.UNRESOLVED,
        )
    else:
        # Missing snap evidence is deliberately UNKNOWN, never zero accessibility.
        routed_origin = RoutedOriginEvidence(
            requested_latitude=request.origin.latitude,
            requested_longitude=request.origin.longitude,
            snap_state=OriginSnapState.UNKNOWN,
            routed_latitude=None,
            routed_longitude=None,
            road_origin_quality=RoadOriginQuality.UNRESOLVED,
        )

    evidence = RoadIsochroneEvidence(
        request_fingerprint=expected_fingerprint,
        request=request,
        routed_origin=routed_origin,
        contours=tuple(ordered),
        warnings=warnings,
        raw_artifact=response.raw_artifact,
        parsed_artifact=response.parsed_artifact,
    )
    validate_road_isochrone_evidence(evidence)
    return evidence
