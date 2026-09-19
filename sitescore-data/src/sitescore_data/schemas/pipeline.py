"""Immutable terminal envelope for SiteScore data-layer pipeline execution.

This module packages already-produced typed artifacts and readiness state. It
performs no provider access, normalization, category aggregation, core
adaptation, scoring, or report generation.

``PipelineStatus.SCORE_READY`` means the data-layer evidence, normalized feature
surface, and scoring-readiness boundary completed successfully and downstream
application-layer category aggregation/scoring is permitted. It does *not* mean
category scores have already been calculated: ``SCORE_READY != SCORED``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sitescore_data.enums import PipelineStatus
from sitescore_data.schemas.common import DataContractVersions, SourceMetadata
from sitescore_data.schemas.competition import CompetitionSnapshot
from sitescore_data.schemas.demographics import DemographicSnapshot
from sitescore_data.schemas.features import (
    DerivedLocationMetrics,
    NormalizedLocationFeatures,
)
from sitescore_data.schemas.geography import ResolvedLocation
from sitescore_data.schemas.parking import ParkingSnapshot
from sitescore_data.schemas.pedestrian import IsochroneSnapshot, PedestrianCatchmentArtifact
from sitescore_data.schemas.readiness import ScoringReadinessResult
from sitescore_data.schemas.road import RoadAccessSnapshot
from sitescore_data.schemas.transit import TransitSnapshot
from sitescore_data.validation import SectorKey, require_aware_datetime


class PipelineReason(StrEnum):
    """Pipeline-level terminal-state reasons, not provider error taxonomy."""

    SCORING_NOT_READY = "scoring_not_ready"
    PIPELINE_STAGE_ERROR = "pipeline_stage_error"


def _require_nonempty_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and trimmed")
    return value


def _require_optional_instance(
    value: object | None,
    expected_type: type,
    *,
    field_name: str,
) -> None:
    if value is not None and not isinstance(value, expected_type):
        raise TypeError(
            f"{field_name} must be a {expected_type.__name__} or None"
        )


@dataclass(frozen=True, slots=True)
class RealDataPipelineResult:
    """Single typed terminal result envelope for one data-layer pipeline run.

    Partial upstream evidence is retained on execution failures. Downstream stage
    monotonicity is enforced only where the canonical data flow makes the
    dependency structural:

    ``normalized_features -> derived_metrics``
    ``scoring_readiness -> normalized_features``

    A ``SCORE_READY`` result stops at the data/app boundary. Category aggregation
    and ``ReadyCategoryScorePayload`` creation happen later in the application
    layer and are intentionally not owned by this envelope.

    ``source_ref`` / ``source_refs`` across the data contracts are opaque
    provenance identities. They are not guaranteed to resolve to
    ``SourceMetadata.source_id``. ``source_metadata`` is therefore a registry of
    source identities known to this result, not a universal registry for every
    artifact/reference namespace. Typed provenance namespaces may be introduced
    in a later contract-major version.
    """

    status: PipelineStatus
    sector_key: SectorKey

    resolved_location: ResolvedLocation | None
    demographics: DemographicSnapshot | None
    pedestrian_catchment: PedestrianCatchmentArtifact | None
    isochrone: IsochroneSnapshot | None
    competition: CompetitionSnapshot | None
    transit: TransitSnapshot | None
    road: RoadAccessSnapshot | None
    parking: ParkingSnapshot | None

    derived_metrics: DerivedLocationMetrics | None
    normalized_features: NormalizedLocationFeatures | None
    scoring_readiness: ScoringReadinessResult | None

    source_metadata: tuple[SourceMetadata, ...]
    pipeline_version: str
    data_contract_versions: DataContractVersions
    generated_at: datetime
    reason_codes: tuple[PipelineReason, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, PipelineStatus):
            raise TypeError("status must be a PipelineStatus")
        if not isinstance(self.sector_key, SectorKey):
            raise TypeError("sector_key must be a SectorKey")

        optional_contracts = (
            ("resolved_location", self.resolved_location, ResolvedLocation),
            ("demographics", self.demographics, DemographicSnapshot),
            (
                "pedestrian_catchment",
                self.pedestrian_catchment,
                PedestrianCatchmentArtifact,
            ),
            ("isochrone", self.isochrone, IsochroneSnapshot),
            ("competition", self.competition, CompetitionSnapshot),
            ("transit", self.transit, TransitSnapshot),
            ("road", self.road, RoadAccessSnapshot),
            ("parking", self.parking, ParkingSnapshot),
            ("derived_metrics", self.derived_metrics, DerivedLocationMetrics),
            (
                "normalized_features",
                self.normalized_features,
                NormalizedLocationFeatures,
            ),
            (
                "scoring_readiness",
                self.scoring_readiness,
                ScoringReadinessResult,
            ),
        )
        for field_name, value, expected_type in optional_contracts:
            _require_optional_instance(
                value,
                expected_type,
                field_name=field_name,
            )

        if not isinstance(self.data_contract_versions, DataContractVersions):
            raise TypeError(
                "data_contract_versions must be a DataContractVersions"
            )

        if self.normalized_features is not None and self.derived_metrics is None:
            raise ValueError(
                "normalized_features requires derived_metrics in the canonical pipeline"
            )

        if self.scoring_readiness is not None and self.normalized_features is None:
            raise ValueError(
                "scoring_readiness requires normalized_features in the canonical pipeline"
            )

        if self.derived_metrics is not None:
            if (
                self.derived_metrics.feature_contract_version
                != self.data_contract_versions.data_feature_contract_version
            ):
                raise ValueError(
                    "derived_metrics feature_contract_version must match "
                    "pipeline data_feature_contract_version"
                )

        if self.normalized_features is not None:
            if (
                self.normalized_features.feature_contract_version
                != self.data_contract_versions.data_feature_contract_version
            ):
                raise ValueError(
                    "normalized_features feature_contract_version must match "
                    "pipeline data_feature_contract_version"
                )
            if (
                self.derived_metrics is not None
                and self.normalized_features.feature_contract_version
                != self.derived_metrics.feature_contract_version
            ):
                raise ValueError(
                    "normalized and derived feature_contract_version values must match"
                )

            transit_fingerprint = (
                self.normalized_features.transit_source_bundle_fingerprint
            )
            if self.transit is not None and transit_fingerprint is not None:
                if transit_fingerprint != self.transit.source_bundle_fingerprint:
                    raise ValueError(
                        "normalized transit source bundle fingerprint must match "
                        "TransitSnapshot source bundle fingerprint"
                    )

            competition_identity = (
                self.normalized_features.competition_measurement_definition_id
            )
            if self.competition is not None and competition_identity is not None:
                if competition_identity != self.competition.measurement_definition_id:
                    raise ValueError(
                        "normalized competition measurement definition must match "
                        "CompetitionSnapshot measurement definition"
                    )

        if not isinstance(self.source_metadata, tuple):
            raise TypeError("source_metadata must be a tuple")
        if any(
            not isinstance(item, SourceMetadata)
            for item in self.source_metadata
        ):
            raise TypeError("source_metadata must contain SourceMetadata values")

        source_ids = tuple(item.source_id for item in self.source_metadata)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_metadata source_id values must be unique")
        if source_ids != tuple(sorted(source_ids)):
            raise ValueError(
                "source_metadata must be deterministically ordered by source_id"
            )

        _require_nonempty_text(
            self.pipeline_version,
            field_name="pipeline_version",
        )
        require_aware_datetime(
            self.generated_at,
            field_name="generated_at",
        )

        if not isinstance(self.reason_codes, tuple):
            raise TypeError("reason_codes must be a tuple")
        if any(
            not isinstance(reason, PipelineReason)
            for reason in self.reason_codes
        ):
            raise TypeError("reason_codes must contain PipelineReason values")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not contain duplicates")

        if self.status is PipelineStatus.SCORE_READY:
            self._validate_score_ready()
        elif self.status is PipelineStatus.NOT_SCORE_READY:
            self._validate_not_score_ready()
        else:
            self._validate_pipeline_error()

    def _validate_score_ready(self) -> None:
        if self.resolved_location is None:
            raise ValueError("SCORE_READY requires resolved_location")
        if self.scoring_readiness is None:
            raise ValueError("SCORE_READY requires scoring_readiness")
        if self.scoring_readiness.is_score_ready is not True:
            raise ValueError("SCORE_READY requires is_score_ready=True")
        if self.normalized_features is None:
            raise ValueError("SCORE_READY requires normalized_features")
        if self.reason_codes:
            raise ValueError("SCORE_READY must not contain pipeline reason codes")

    def _validate_not_score_ready(self) -> None:
        if self.scoring_readiness is None:
            raise ValueError("NOT_SCORE_READY requires scoring_readiness")
        if self.scoring_readiness.is_score_ready is not False:
            raise ValueError("NOT_SCORE_READY requires is_score_ready=False")
        if self.reason_codes != (PipelineReason.SCORING_NOT_READY,):
            raise ValueError(
                "NOT_SCORE_READY reason_codes must equal (SCORING_NOT_READY,)"
            )

    def _validate_pipeline_error(self) -> None:
        if self.scoring_readiness is not None:
            raise ValueError(
                "PIPELINE_ERROR must not contain scoring_readiness; "
                "readiness is the terminal data-layer boundary"
            )
        if self.reason_codes != (PipelineReason.PIPELINE_STAGE_ERROR,):
            raise ValueError(
                "PIPELINE_ERROR reason_codes must equal (PIPELINE_STAGE_ERROR,)"
            )
