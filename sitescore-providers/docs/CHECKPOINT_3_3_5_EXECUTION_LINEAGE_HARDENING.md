# Checkpoint 3.3-5 — Pedestrian Execution / Lineage Hardening Audit

Status: HARDENED — READY TO LOCK review

This record is limited to the requested source-level audit. It does not advance to Checkpoint 3.3-6.

## AUDIT-001 — WalkingBudgetPolicy vs Valhalla execution limits

Previous source behavior: `WalkingBudgetPolicy` accepted one-or-many scales and `build_valhalla_isochrone_body()` emitted every scale as a time contour. No deployed `max_contours` / `max_time_contour` configuration was bound to canonical execution.

Disposition: ISSUE CONFIRMED / HARDENED.

Added immutable `ValhallaIsochroneExecutionPolicy(policy_id, policy_version, max_contours, max_time_contour_minutes)`. A `PedestrianIsochroneRequest` is invalid if its scale count exceeds `max_contours` or any time contour exceeds the configured maximum. V1 rejects before transport; it does not split requests. Execution-policy identity is included through `ValhallaExecutionBinding` in request and derivation identity.

## AUDIT-002 — Deployment binding

Previous source behavior: `PedestrianIsochroneClient` accepted an arbitrary `/isochrone` endpoint independently of the request's declared graph/engine compatibility.

Disposition: ISSUE CONFIRMED / HARDENED.

Added immutable `ValhallaExecutionBinding(binding_id, binding_version, graph_compatibility, execution_policy)`. It is a trusted deployment/config attestation, not a cryptographic or runtime proof. The client is constructed with one binding and rejects requests carrying any other binding before network execution. Binding identity commits to graph compatibility, graph content hash/artifact ref, routing-engine manifest and service execution policy. Endpoint URL remains execution metadata and is not a semantic measurement identity.

No `/status` graph-hash claim is made. Exact graph content identity is trusted from the deployment/build pipeline because the canonical provider surface does not receive a raw graph artifact from the running service.

## AUDIT-003 — Warnings

Previous source behavior: top-level `warnings` were silently ignored.

Disposition: ISSUE CONFIRMED / HARDENED.

Added immutable `ValhallaWarningEvidence`. Parsed warnings are retained in `PedestrianIsochroneEvidence` and participate in evidence identity. V1 intentionally invents no warning-code taxonomy: every warning is `UNRESOLVED`. Canonical AVAILABLE frozen output rejects any non-empty warning set. This conservatively covers clamping/semantic-drift and unknown warnings without memory-derived code mappings.

## AUDIT-004 — show_locations role resolution

Previous source behavior: with two returned points, the parser found an exact-input coordinate and treated the other occurrence as snapped; if both coordinates were numerically identical it fabricated roles by feature position.

Disposition: ISSUE CONFIRMED / HARDENED.

Role resolution is now order-independent. Exactly one returned point matching the requested coordinate allows the other point to be interpreted as snapped-node evidence. Two numerically identical matches are ambiguous and produce `OriginSnapState.UNKNOWN`; one/missing role also remains UNKNOWN. Feature ordering cannot change the semantic result.

## AUDIT-005 — network / graph content provenance

Network side previous behavior was already clean: `PedestrianNetworkSourceEvidence` enforces `raw_artifact.content_hash == manifest.network_content_hash`, exact provider identity, SourceMetadata coherence and PERSIST replay semantics.

Graph side is explicitly a trusted deployment boundary. `PedestrianGraphCompatibility` carries graph content hash + artifact ref, while `ValhallaExecutionBinding` attests that a particular endpoint/process deployment corresponds to that compatibility and service config. Runtime execution does not claim to independently recompute or retrieve the exact graph content hash.

## Regression summary

Added coverage for:
- exact execution limits accepted
- over max contours rejected before network
- over max time contour rejected before network
- execution limit changes alter request/derivation identity
- client binding mismatch rejected before network
- engine/service-config binding changes alter identity
- warnings retained and canonical AVAILABLE frozen build rejected
- show_locations feature-order reversal invariant
- identical-role ambiguity -> UNKNOWN
- missing one role -> UNKNOWN
- network raw content hash mismatch -> rejected

## Scope preservation

Unchanged concepts: frozen sitescore-data pedestrian contracts, provider neutrality, graph compatibility concept, walking-budget calibration values, geometry canonicalization, area sidecar, no-snap != zero, no straight-line fallback, Checkpoints 3.3-1 through 3.3-4.

No GTFS, road, parking, demographic overlay, ECDF, normalization or core/app integration was added.
