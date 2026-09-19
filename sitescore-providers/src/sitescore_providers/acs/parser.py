"""Parse canonical ACS API rows into immutable statistical evidence sidecars."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ..errors import ProviderInvariantError, ProviderMalformedResponseError
from .client import ACS_PARSER_ID, ParsedACSResponse, _provider_identity
from .models import (
    ACSDatasetManifest,
    ACSParsedEvidenceResult,
    ACSRequest,
    ACSRowState,
    ACSStatisticalEvidence,
    ACSStatisticalValueState,
)

# Official Census ACS special-value semantics. Raw values/annotations are retained;
# special states are never emitted as ordinary numeric estimates.
_ESTIMATE_SENTINELS = {
    Decimal("-666666666"): ACSStatisticalValueState.MISSING,
    Decimal("-999999999"): ACSStatisticalValueState.SUPPRESSED,
    Decimal("-888888888"): ACSStatisticalValueState.NOT_APPLICABLE,
}
_MOE_SENTINELS = {
    Decimal("-222222222"): ACSStatisticalValueState.MISSING,
    Decimal("-333333333"): ACSStatisticalValueState.MISSING,
    Decimal("-555555555"): ACSStatisticalValueState.CONTROLLED,
    Decimal("-666666666"): ACSStatisticalValueState.MISSING,
    Decimal("-999999999"): ACSStatisticalValueState.SUPPRESSED,
    Decimal("-888888888"): ACSStatisticalValueState.NOT_APPLICABLE,
}


def _text_or_none(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderMalformedResponseError(f"{field_name} must be string or null")
    return value


def _numeric(value: str | None, *, annotation: str | None, is_moe: bool) -> tuple[int | float | None, ACSStatisticalValueState]:
    if value is None:
        return None, ACSStatisticalValueState.MISSING
    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ProviderMalformedResponseError("ACS estimate/MOE must be numeric string or null") from exc
    sentinel_map = _MOE_SENTINELS if is_moe else _ESTIMATE_SENTINELS
    if decimal_value in sentinel_map:
        return None, sentinel_map[decimal_value]
    if not decimal_value.is_finite():
        raise ProviderMalformedResponseError("ACS estimate/MOE must be finite")
    # Any non-empty ACS annotation means the corresponding E/M cell must not
    # be exposed as ordinary numeric evidence. Sentinel semantics above take
    # precedence because they are explicitly documented numeric encodings.
    if annotation not in {None, ""}:
        return None, ACSStatisticalValueState.ANNOTATED
    if decimal_value == decimal_value.to_integral_value():
        return int(decimal_value), ACSStatisticalValueState.VALUE
    return float(decimal_value), ACSStatisticalValueState.VALUE


def _expected_geo_columns(request: ACSRequest) -> tuple[str, ...]:
    if request.geography.geography_type.value == "tract":
        return ("state", "county", "tract")
    return ("state", "county", "tract", "block group")


def _expected_geo_values(request: ACSRequest) -> dict[str, str]:
    geoid = request.geography.geography_id
    values = {"state": geoid[:2], "county": geoid[2:5], "tract": geoid[5:11]}
    if request.geography.geography_type.value == "block_group":
        values["block group"] = geoid[11:12]
    return values


def parse_acs_statistical_evidence(
    *,
    response: ParsedACSResponse,
    request: ACSRequest,
    manifest: ACSDatasetManifest,
) -> ACSParsedEvidenceResult:
    if not isinstance(response, ParsedACSResponse):
        raise TypeError("response must be a ParsedACSResponse")
    if not isinstance(request, ACSRequest):
        raise TypeError("request must be an ACSRequest")
    if not isinstance(manifest, ACSDatasetManifest):
        raise TypeError("manifest must be an ACSDatasetManifest")
    if response.raw_artifact.request_fingerprint != request.request_fingerprint:
        raise ProviderInvariantError("ACS raw artifact request fingerprint does not match parser request")
    if response.raw_artifact.provider_identity != _provider_identity(manifest):
        raise ProviderInvariantError("ACS raw artifact provider identity does not match active dataset manifest")
    if response.parsed_artifact.parser_id != ACS_PARSER_ID:
        raise ProviderInvariantError("ACS parsed artifact parser_id does not match the canonical ACS parser")
    if response.parsed_artifact.parser_version != manifest.parser_version:
        raise ProviderInvariantError("ACS parsed artifact parser_version does not match active dataset manifest")
    root = response.parsed_value
    if not root:
        raise ProviderMalformedResponseError("ACS response must include a header row")
    header = root[0]
    if not isinstance(header, list) or not header or not all(isinstance(item, str) and item for item in header):
        raise ProviderMalformedResponseError("ACS header must be a non-empty string array")
    if len(header) != len(set(header)):
        raise ProviderInvariantError("ACS response contains duplicate header columns")
    expected_geo_columns = _expected_geo_columns(request)
    expected_columns = set(request.variable_ids) | set(expected_geo_columns)
    missing_columns = expected_columns - set(header)
    if missing_columns:
        raise ProviderMalformedResponseError(f"ACS response missing requested columns: {sorted(missing_columns)}")
    unexpected_columns = set(header) - expected_columns
    if unexpected_columns:
        raise ProviderInvariantError(f"ACS response contains unexpected columns: {sorted(unexpected_columns)}")
    if len(root) == 1:
        return ACSParsedEvidenceResult(ACSRowState.NO_DATA, (), response.parsed_artifact)
    if len(root) != 2:
        raise ProviderInvariantError("exact ACS geography query must return at most one data row")
    row = root[1]
    if not isinstance(row, list) or len(row) != len(header):
        raise ProviderMalformedResponseError("ACS data row width must equal header width")
    values = dict(zip(header, row, strict=True))
    expected_geo_values = _expected_geo_values(request)
    for column, expected in expected_geo_values.items():
        actual = values[column]
        if not isinstance(actual, str) or actual != expected:
            raise ProviderInvariantError(f"ACS response geography mismatch for {column}")

    by_key = manifest.variable_manifest.by_semantic_key
    evidence: list[ACSStatisticalEvidence] = []
    for semantic_key in request.semantic_keys:
        spec = by_key.get(semantic_key)
        if spec is None:
            raise ProviderInvariantError("ACS request semantic key is absent from variable manifest")
        if not set(spec.request_variable_ids).issubset(request.variable_ids):
            raise ProviderInvariantError("ACS request split a variable spec across requests")
        estimate_raw = _text_or_none(values[spec.estimate_variable_id], field_name=spec.estimate_variable_id)
        moe_raw = _text_or_none(values[spec.margin_of_error_variable_id], field_name=spec.margin_of_error_variable_id)
        estimate_annotation = _text_or_none(values[spec.estimate_annotation_variable_id], field_name=spec.estimate_annotation_variable_id) if spec.estimate_annotation_variable_id else None
        moe_annotation = _text_or_none(values[spec.margin_of_error_annotation_variable_id], field_name=spec.margin_of_error_annotation_variable_id) if spec.margin_of_error_annotation_variable_id else None
        estimate, estimate_state = _numeric(estimate_raw, annotation=estimate_annotation, is_moe=False)
        moe, moe_state = _numeric(moe_raw, annotation=moe_annotation, is_moe=True)
        evidence.append(
            ACSStatisticalEvidence(
                semantic_key=spec.semantic_key,
                estimate_variable_id=spec.estimate_variable_id,
                margin_of_error_variable_id=spec.margin_of_error_variable_id,
                estimate_annotation_variable_id=spec.estimate_annotation_variable_id,
                margin_of_error_annotation_variable_id=spec.margin_of_error_annotation_variable_id,
                request_fingerprint=request.request_fingerprint,
                estimate=estimate,
                margin_of_error=moe,
                estimate_state=estimate_state,
                margin_of_error_state=moe_state,
                estimate_raw_value=estimate_raw,
                margin_of_error_raw_value=moe_raw,
                estimate_annotation=estimate_annotation,
                margin_of_error_annotation=moe_annotation,
                geography_type=request.geography.geography_type,
                geography_id=request.geography.geography_id,
                dataset_release=manifest.dataset_release,
                vintage=manifest.vintage,
                dataset_manifest_identity=manifest.identity,
                raw_content_hash=response.raw_artifact.content_hash,
                parsed_artifact_identity=response.parsed_artifact.identity,
            )
        )
    return ACSParsedEvidenceResult(ACSRowState.FOUND, tuple(evidence), response.parsed_artifact)
