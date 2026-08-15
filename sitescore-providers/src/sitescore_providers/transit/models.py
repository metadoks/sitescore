"""Immutable GTFS Static provider contracts for checkpoint 3.3-6."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
import math
from statistics import median
from typing import Iterable

from sitescore_data import ValidityState
from sitescore_data.schemas.common import SourceMetadata

from .._validation import require_canonical_id, require_nonempty_text
from ..artifacts import ParsedArtifact, RawAcquisitionArtifact
from ..hashing import CANONICALIZATION_VERSION, ContentHash, hash_canonical
from ..identity import ProviderIdentity

GTFS_PROVIDER_KEY = "gtfs_static"
GTFS_DOMAIN = "transit"
GTFS_DATASET = "gtfs_schedule"
GTFS_PARSER_ID = "gtfs_static_zip"
GTFS_BUNDLE_GRAMMAR = "v1"
GTFS_DERIVATION_GRAMMAR = "v1"


def _mutable(value: str) -> bool:
    return value.strip().lower() in {"latest", "current", "live", "today", "now"}


def _text(value: str, name: str) -> str:
    require_nonempty_text(value, field_name=name)
    return value


@dataclass(frozen=True, slots=True)
class GTFSFeedManifest:
    manifest_version: str
    feed_id: str
    feed_provider: str
    dataset_release: str
    schema_version: str
    parser_version: str
    feed_content_hash: ContentHash
    acquisition_id: str
    acquisition_version: str

    def __post_init__(self) -> None:
        require_nonempty_text(self.manifest_version, field_name="manifest_version")
        require_canonical_id(self.feed_id, field_name="feed_id")
        require_nonempty_text(self.feed_provider, field_name="feed_provider")
        require_nonempty_text(self.dataset_release, field_name="dataset_release")
        require_nonempty_text(self.schema_version, field_name="schema_version")
        require_nonempty_text(self.parser_version, field_name="parser_version")
        if _mutable(self.dataset_release):
            raise ValueError("dataset_release must be an exact immutable release identity")
        if not isinstance(self.feed_content_hash, ContentHash):
            raise TypeError("feed_content_hash must be a ContentHash")
        require_canonical_id(self.acquisition_id, field_name="acquisition_id")
        require_nonempty_text(self.acquisition_version, field_name="acquisition_version")

    @property
    def provider_identity(self) -> ProviderIdentity:
        return ProviderIdentity(
            provider_key=GTFS_PROVIDER_KEY,
            domain=GTFS_DOMAIN,
            dataset=f"{GTFS_DATASET}:{self.feed_id}",
            dataset_release=self.dataset_release,
            vintage=None,
            schema_version=self.schema_version,
            parser_version=self.parser_version,
            method_version=self.manifest_version,
        )

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({
            "grammar_version": GTFS_BUNDLE_GRAMMAR,
            "canonicalization_version": CANONICALIZATION_VERSION,
            "manifest_version": self.manifest_version,
            "feed_id": self.feed_id,
            "feed_provider": self.feed_provider,
            "dataset_release": self.dataset_release,
            "schema_version": self.schema_version,
            "parser_version": self.parser_version,
            "feed_content_hash": str(self.feed_content_hash),
            "acquisition_id": self.acquisition_id,
            "acquisition_version": self.acquisition_version,
        })


@dataclass(frozen=True, slots=True)
class GTFSServiceCalendarPolicy:
    policy_id: str
    policy_version: str
    calendar_dates_override_base: bool = True
    allow_calendar_dates_only: bool = True

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if self.calendar_dates_override_base is not True:
            raise ValueError("GTFS V1 requires calendar_dates to override base calendar")
        if self.allow_calendar_dates_only is not True:
            raise ValueError("GTFS V1 must support calendar_dates-only feeds")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({"grammar":"gtfs_calendar.v1","canonicalization_version":CANONICALIZATION_VERSION,
            "policy_id":self.policy_id,"policy_version":self.policy_version,
            "calendar_dates_override_base":True,"allow_calendar_dates_only":True})


@dataclass(frozen=True, slots=True)
class GTFSStopHierarchyPolicy:
    policy_id: str
    policy_version: str
    hierarchy_version: str = "gtfs_location_type_parent_station.v1"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        require_nonempty_text(self.hierarchy_version, field_name="hierarchy_version")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({"grammar":"gtfs_stop_hierarchy.v1","canonicalization_version":CANONICALIZATION_VERSION,
            "policy_id":self.policy_id,"policy_version":self.policy_version,"hierarchy_version":self.hierarchy_version})


@dataclass(frozen=True, slots=True)
class TransitBoardingPolicy:
    policy_id: str
    policy_version: str
    allowed_pickup_types: tuple[int, ...] = (0, 2, 3)
    timestamp_method: str = "earliest_reachable_boarding_departure"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if self.allowed_pickup_types != tuple(sorted(set(self.allowed_pickup_types))):
            raise ValueError("allowed_pickup_types must be unique sorted")
        if any(x not in {0,2,3} for x in self.allowed_pickup_types):
            raise ValueError("pickup_type=1 cannot be boarding-capable")
        if self.timestamp_method != "earliest_reachable_boarding_departure":
            raise ValueError("unsupported V1 timestamp_method")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({"grammar":"gtfs_boarding.v1","canonicalization_version":CANONICALIZATION_VERSION,
            "policy_id":self.policy_id,"policy_version":self.policy_version,"allowed_pickup_types":self.allowed_pickup_types,
            "timestamp_method":self.timestamp_method})


@dataclass(frozen=True, slots=True)
class GTFSFrequencyPolicy:
    policy_id: str
    policy_version: str
    exact_times_one_method: str = "expand_exact_instances"
    inexact_method: str = "integrated_headway_departure_equivalents"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if self.exact_times_one_method != "expand_exact_instances":
            raise ValueError("unsupported exact_times=1 method")
        if self.inexact_method != "integrated_headway_departure_equivalents":
            raise ValueError("unsupported exact_times=0 method")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({"grammar":"gtfs_frequency.v1","canonicalization_version":CANONICALIZATION_VERSION,
            "policy_id":self.policy_id,"policy_version":self.policy_version,
            "exact_times_one_method":self.exact_times_one_method,"inexact_method":self.inexact_method})


@dataclass(frozen=True, slots=True)
class TransitWeeklyProfilePolicy:
    policy_id: str
    policy_version: str
    representative_statistic: str
    reference_dates: tuple[date, ...]
    service_clock_semantics: str = "agency_local_service_clock"

    def __post_init__(self) -> None:
        require_canonical_id(self.policy_id, field_name="policy_id")
        require_nonempty_text(self.policy_version, field_name="policy_version")
        if self.representative_statistic != "median_same_weekday_hour":
            raise ValueError("V1 representative_statistic must be median_same_weekday_hour")
        if not isinstance(self.reference_dates, tuple) or not self.reference_dates:
            raise ValueError("reference_dates must be a non-empty tuple")
        if any(not isinstance(d, date) for d in self.reference_dates):
            raise TypeError("reference_dates must contain dates")
        if self.reference_dates != tuple(sorted(set(self.reference_dates))):
            raise ValueError("reference_dates must be unique sorted")
        if self.service_clock_semantics != "agency_local_service_clock":
            raise ValueError("V1 uses agency-local GTFS service-clock bins")

    @property
    def identity(self) -> ContentHash:
        return hash_canonical({"grammar":"gtfs_weekly_profile.v1","canonicalization_version":CANONICALIZATION_VERSION,
            "policy_id":self.policy_id,"policy_version":self.policy_version,"representative_statistic":self.representative_statistic,
            "reference_dates":[d.isoformat() for d in self.reference_dates],"service_clock_semantics":self.service_clock_semantics})


@dataclass(frozen=True, slots=True)
class TransitSourceBundle:
    bundle_id: str
    bundle_version: str
    feed_manifest: GTFSFeedManifest
    calendar_policy: GTFSServiceCalendarPolicy
    hierarchy_policy: GTFSStopHierarchyPolicy
    boarding_policy: TransitBoardingPolicy
    frequency_policy: GTFSFrequencyPolicy
    component_file_hashes: tuple[tuple[str, ContentHash], ...]

    def __post_init__(self) -> None:
        require_canonical_id(self.bundle_id, field_name="bundle_id")
        require_nonempty_text(self.bundle_version, field_name="bundle_version")
        if not isinstance(self.feed_manifest, GTFSFeedManifest): raise TypeError("feed_manifest")
        names=[n for n,_ in self.component_file_hashes]
        if names != sorted(set(names)):
            raise ValueError("component_file_hashes must be unique sorted by filename")
        for n,h in self.component_file_hashes:
            require_nonempty_text(n, field_name="component filename")
            if not isinstance(h,ContentHash): raise TypeError("component hash")

    @property
    def fingerprint(self) -> str:
        h=hash_canonical({"grammar":GTFS_BUNDLE_GRAMMAR,"canonicalization_version":CANONICALIZATION_VERSION,
            "bundle_id":self.bundle_id,"bundle_version":self.bundle_version,"feed_manifest_identity":str(self.feed_manifest.identity),
            "calendar_policy":str(self.calendar_policy.identity),"hierarchy_policy":str(self.hierarchy_policy.identity),
            "boarding_policy":str(self.boarding_policy.identity),"frequency_policy":str(self.frequency_policy.identity),
            "component_file_hashes":[(n,str(v)) for n,v in self.component_file_hashes]})
        return f"gtfs_bundle.{h.algorithm.value}_{h.digest}"


class GTFSFeedValidityState(StrEnum):
    VALID="valid"; DERIVED_VALIDITY="derived_validity"; OUT_OF_VALIDITY="out_of_validity"; UNKNOWN="unknown"


@dataclass(frozen=True, slots=True)
class GTFSStop:
    stop_id:str; location_type:int; parent_station:str|None; lat:float|None; lon:float|None

@dataclass(frozen=True, slots=True)
class GTFSRoute:
    route_id:str

@dataclass(frozen=True, slots=True)
class GTFSTrip:
    trip_id:str; route_id:str; service_id:str

@dataclass(frozen=True, slots=True)
class GTFSStopTime:
    trip_id:str; stop_id:str; stop_sequence:int; departure_seconds:int|None; pickup_type:int

@dataclass(frozen=True, slots=True)
class GTFSCalendar:
    service_id:str; weekdays:tuple[bool,...]; start_date:date; end_date:date

@dataclass(frozen=True, slots=True)
class GTFSCalendarDate:
    service_id:str; date:date; exception_type:int

@dataclass(frozen=True, slots=True)
class GTFSFrequency:
    trip_id:str; start_seconds:int; end_seconds:int; headway_secs:int; exact_times:int

@dataclass(frozen=True, slots=True)
class GTFSFeedInfo:
    feed_start_date:date|None; feed_end_date:date|None; feed_version:str|None

@dataclass(frozen=True, slots=True)
class ParsedGTFSFeed:
    bundle: TransitSourceBundle
    raw_artifact: RawAcquisitionArtifact
    parsed_artifact: ParsedArtifact
    source_metadata: SourceMetadata
    agency_timezone: str
    stops: tuple[GTFSStop,...]
    routes: tuple[GTFSRoute,...]
    trips: tuple[GTFSTrip,...]
    stop_times: tuple[GTFSStopTime,...]
    calendars: tuple[GTFSCalendar,...]
    calendar_dates: tuple[GTFSCalendarDate,...]
    frequencies: tuple[GTFSFrequency,...]
    feed_info: GTFSFeedInfo|None
    validity_start: date|None
    validity_end: date|None
    validity_state: GTFSFeedValidityState

    def __post_init__(self) -> None:
        if self.raw_artifact.provider_identity != self.bundle.feed_manifest.provider_identity:
            raise ValueError("raw provider identity does not match GTFS manifest")
        if self.raw_artifact.content_hash != self.bundle.feed_manifest.feed_content_hash:
            raise ValueError("raw GTFS ZIP content hash does not match feed manifest")
        if self.parsed_artifact.raw_content_hash != self.raw_artifact.content_hash:
            raise ValueError("parsed/raw GTFS lineage mismatch")
        if self.source_metadata.content_hash != str(self.raw_artifact.content_hash):
            raise ValueError("SourceMetadata content hash mismatch")
        identity=self.raw_artifact.provider_identity
        if (self.source_metadata.provider != identity.provider_key or self.source_metadata.dataset != identity.dataset
            or self.source_metadata.dataset_release != identity.dataset_release or self.source_metadata.vintage != identity.vintage
            or self.source_metadata.schema_version != identity.schema_version):
            raise ValueError("SourceMetadata semantic identity does not match GTFS raw provider identity")


@dataclass(frozen=True, slots=True)
class ReachableTransitStopSet:
    source_bundle_fingerprint:str
    pedestrian_derivation_identity:str
    walking_budget_policy_identity:str
    membership_method_id:str
    membership_method_version:str
    reachable_stop_ids:tuple[str,...]
    walk_catchment_ref:str
    access_geometry_quality:str
    source_refs:tuple[str,...]=()

    def __post_init__(self) -> None:
        require_nonempty_text(self.source_bundle_fingerprint, field_name="source_bundle_fingerprint")
        for name in ("pedestrian_derivation_identity","walking_budget_policy_identity","membership_method_id","membership_method_version","walk_catchment_ref","access_geometry_quality"):
            require_nonempty_text(getattr(self,name), field_name=name)
        if self.reachable_stop_ids != tuple(sorted(set(self.reachable_stop_ids))):
            raise ValueError("reachable_stop_ids must be unique sorted")
        if not isinstance(self.source_refs,tuple): raise TypeError("source_refs must be tuple")
        if self.source_refs != tuple(sorted(set(self.source_refs))): raise ValueError("source_refs must be unique sorted")
        for ref in self.source_refs: require_canonical_id(ref, field_name="source_ref")

    @property
    def identity(self)->ContentHash:
        return hash_canonical({"grammar":"reachable_transit_stops.v1","canonicalization_version":CANONICALIZATION_VERSION,
            "source_bundle_fingerprint":self.source_bundle_fingerprint,"pedestrian_derivation_identity":self.pedestrian_derivation_identity,
            "walking_budget_policy_identity":self.walking_budget_policy_identity,"membership_method_id":self.membership_method_id,
            "membership_method_version":self.membership_method_version,"reachable_stop_ids":self.reachable_stop_ids,
            "walk_catchment_ref":self.walk_catchment_ref,"access_geometry_quality":self.access_geometry_quality,
            "source_refs":self.source_refs})


@dataclass(frozen=True, slots=True)
class TransitWeeklyServiceProfile:
    exact_departures: tuple[int,...]
    frequency_equivalents: tuple[float,...]
    total_equivalents: tuple[float,...]
    source_bundle_fingerprint: str
    derivation_identity: ContentHash

    def __post_init__(self)->None:
        if len(self.exact_departures)!=168 or len(self.frequency_equivalents)!=168 or len(self.total_equivalents)!=168:
            raise ValueError("weekly profile must contain exactly 168 bins")
        for i,(e,f,t) in enumerate(zip(self.exact_departures,self.frequency_equivalents,self.total_equivalents)):
            if not isinstance(e,int) or isinstance(e,bool) or e<0: raise ValueError(f"invalid exact bin {i}")
            if not isinstance(f,(int,float)) or isinstance(f,bool) or not math.isfinite(f) or f<0: raise ValueError(f"invalid frequency bin {i}")
            if not math.isclose(e+f,t,rel_tol=1e-12,abs_tol=1e-12): raise ValueError("total profile mismatch")

