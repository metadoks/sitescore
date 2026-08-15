"""Census Geocoder JSON parsers from canonical parsed primitives into typed evidence."""

from __future__ import annotations

from typing import Any

from ..errors import ProviderMalformedResponseError, ProviderInvariantError
from ..artifacts import ParsedArtifact
from ..identity import RequestFingerprint
from .models import (
    CensusCoordinates,
    CensusGeocodeCandidate,
    CensusGeocodeEvidence,
    CensusGeocodePrecision,
    CensusGeographyEvidence,
    CensusGeographyManifest,
    CensusGeographyRecord,
    CensusMatchState,
)


def _mapping(value: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderMalformedResponseError(f"{path} must be an object")
    return value


def _list(value: Any, *, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderMalformedResponseError(f"{path} must be an array")
    return value


def _text(value: Any, *, path: str, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProviderMalformedResponseError(f"{path} must be non-empty text")
    return value.strip()


def _response_benchmark(result: dict[str, Any]) -> str:
    input_value = _mapping(result.get("input"), path="result.input")
    benchmark = _mapping(input_value.get("benchmark"), path="result.input.benchmark")
    return _text(benchmark.get("benchmarkName"), path="result.input.benchmark.benchmarkName")  # type: ignore[return-value]


def _response_vintage(result: dict[str, Any]) -> str:
    input_value = _mapping(result.get("input"), path="result.input")
    vintage = _mapping(input_value.get("vintage"), path="result.input.vintage")
    return _text(vintage.get("vintageName"), path="result.input.vintage.vintageName")  # type: ignore[return-value]


def parse_geocode_evidence(
    *,
    parsed_value: Any,
    parsed_artifact: ParsedArtifact,
    request_fingerprint: RequestFingerprint,
    manifest: CensusGeographyManifest,
) -> CensusGeocodeEvidence:
    top = _mapping(parsed_value, path="response")
    result = _mapping(top.get("result"), path="result")
    response_benchmark = _response_benchmark(result)
    if response_benchmark != manifest.geocoder_benchmark:
        raise ProviderInvariantError("Census response benchmark does not match pinned manifest")
    matches = _list(result.get("addressMatches"), path="result.addressMatches")
    candidates: list[CensusGeocodeCandidate] = []
    for index, item in enumerate(matches):
        match = _mapping(item, path=f"result.addressMatches[{index}]")
        coordinates = _mapping(match.get("coordinates"), path=f"result.addressMatches[{index}].coordinates")
        # Census API uses x=longitude and y=latitude. The typed artifact stores lat/lon explicitly.
        try:
            typed_coordinates = CensusCoordinates(
                latitude=coordinates.get("y"),
                longitude=coordinates.get("x"),
            )
        except (TypeError, ValueError) as exc:
            raise ProviderMalformedResponseError("invalid Census x/y coordinates") from exc
        tiger_line = match.get("tigerLine")
        tiger_line_id = None
        tiger_line_side = None
        if tiger_line is not None:
            tiger = _mapping(tiger_line, path=f"result.addressMatches[{index}].tigerLine")
            tiger_line_id = _text(tiger.get("tigerLineId"), path="tigerLine.tigerLineId", optional=True)
            tiger_line_side = _text(tiger.get("side"), path="tigerLine.side", optional=True)
        match_type = _text(match.get("matchType"), path="matchType", optional=True)
        candidates.append(
            CensusGeocodeCandidate(
                matched_address=_text(match.get("matchedAddress"), path="matchedAddress"),  # type: ignore[arg-type]
                coordinates=typed_coordinates,
                tiger_line_id=tiger_line_id,
                tiger_line_side=tiger_line_side,
                census_match_type=match_type,
            )
        )
    if len(candidates) == 0:
        state = CensusMatchState.NO_MATCH
        precision = CensusGeocodePrecision.UNKNOWN
    elif len(candidates) == 1:
        state = CensusMatchState.MATCHED
        precision = CensusGeocodePrecision.ADDRESS_RANGE_INTERPOLATED
    else:
        state = CensusMatchState.AMBIGUOUS
        precision = CensusGeocodePrecision.ADDRESS_RANGE_INTERPOLATED
    return CensusGeocodeEvidence(
        request_fingerprint=request_fingerprint,
        match_state=state,
        candidates=tuple(candidates),
        benchmark=response_benchmark,
        precision=precision,
        parsed_artifact=parsed_artifact,
    )


def parse_geography_evidence(
    *,
    parsed_value: Any,
    parsed_artifact: ParsedArtifact,
    request_fingerprint: RequestFingerprint,
    coordinates: CensusCoordinates,
    manifest: CensusGeographyManifest,
) -> CensusGeographyEvidence:
    top = _mapping(parsed_value, path="response")
    result = _mapping(top.get("result"), path="result")
    response_benchmark = _response_benchmark(result)
    response_vintage = _response_vintage(result)
    if response_benchmark != manifest.geocoder_benchmark:
        raise ProviderInvariantError("Census geography response benchmark does not match pinned manifest")
    if response_vintage != manifest.geography_vintage:
        raise ProviderInvariantError("Census geography response vintage does not match pinned manifest")
    geographies = _mapping(result.get("geographies"), path="result.geographies")
    records: list[CensusGeographyRecord] = []
    for layer in manifest.supported_layers:
        matches: list[tuple[str, dict[str, Any]]] = []
        for response_key in layer.response_keys:
            raw_records = geographies.get(response_key)
            if raw_records is None:
                continue
            layer_records = _list(raw_records, path=f"result.geographies.{response_key}")
            if len(layer_records) > 1:
                raise ProviderInvariantError(
                    f"coordinate lookup returned multiple records for {response_key}"
                )
            if layer_records:
                matches.append((response_key, _mapping(layer_records[0], path=f"result.geographies.{response_key}[0]")))
        if len(matches) > 1:
            raise ProviderInvariantError(
                f"coordinate lookup resolved multiple Census layers for {layer.geography_type.value}"
            )
        if not matches:
            if layer.required:
                raise ProviderInvariantError(
                    f"required Census geography layer missing for {layer.geography_type.value}"
                )
            continue
        response_key, record = matches[0]
        records.append(
            CensusGeographyRecord(
                geography_type=layer.geography_type,
                geoid=_text(record.get("GEOID"), path="GEOID"),  # type: ignore[arg-type]
                name=_text(record.get("NAME"), path="NAME"),  # type: ignore[arg-type]
                response_layer=response_key,
            )
        )
    # Manifest order is the deterministic order; absent optional layers are simply omitted.
    return CensusGeographyEvidence(
        request_fingerprint=request_fingerprint,
        coordinates=coordinates,
        benchmark=response_benchmark,
        geography_vintage=response_vintage,
        manifest_identity=manifest.identity,
        records=tuple(records),
        parsed_artifact=parsed_artifact,
    )
