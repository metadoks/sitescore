# Checkpoint 3.3-7 Road Hardening

Only ROAD-001 and ROAD-002 were changed.

## ROAD-001 — per-scale measurement-policy identity

`build_measurement_policy_identity()` is the single canonical helper used by both the frozen road method identity and `RoadDerivationEvidence.measurement_policy_identity`.

Its preimage is canonicalized in `RoadDriveBudgetPolicy.scales` order and each entry contains:

- `scale_id`
- `area_policy_identity`
- `network_measurement_method_id`
- `network_measurement_method_version`

Caller measurement tuple ordering does not affect the identity. Reassigning policies/methods between scales does.

## ROAD-002 — manifest-bound network media type

`RoadNetworkManifest` now carries exact `media_type` as artifact-representation semantics distinct from `format_id` / `format_version`.

The field is non-empty, trimmed, immutable manifest identity input. Network acquisition request identity also commits to it.

`build_network_source_evidence()` emits `RawAcquisitionArtifact.media_type = manifest.media_type`, and `RoadNetworkSourceEvidence` rejects a direct-constructed raw artifact whose media type differs from the active manifest.

No provider-specific OSM media type constant remains in the road network builder.

## Verification

- provider tests: 375/375 PASS
- sitescore-data: 361/361 PASS
- sitescore-core: 86/86 PASS
- runtime dependency: `sitescore-data==0.1.0` only
- `sitescore-core` imports: 0
- locked 3.3-1–3.3-6 production source diff: changed=0, missing=0
- CONTRACT_CHANGE_REQUIRED: 0
