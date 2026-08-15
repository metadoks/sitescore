# Checkpoint 3.3-8 Parking Hardening

Status: HARDENED — READY TO LOCK (pending independent review)

This patch is limited to PARK-001 and PARK-002 from the final source-level review.
No road+parking composite, ECDF, normalization, benchmark, app/core integration, or cross-source fuzzy reconciliation was added.

## PARK-001 — active road/pedestrian compatibility

`ParkingAccessibilityCompatibility` is an immutable/versioned trusted orchestration/configuration artifact. It binds the parking derivation to the expected upstream road and pedestrian semantics:

- `expected_road_derivation_identity`
- `expected_graph_compatibility_identity`
- `expected_drive_budget_policy_identity`
- `expected_pedestrian_derivation_identity`
- `expected_walking_budget_policy_identity`

`build_parking_snapshot()` requires this artifact and rejects motor/pedestrian reachability evidence whose upstream identities do not match it. Its identity is included in the parking measurement identity and is preserved explicitly in `ParkingDerivationEvidence`.

This is a trusted compatibility boundary, not a cryptographic proof and not an import dependency on road/pedestrian implementation packages.

## PARK-002 — explicit dynamic link semantics

`ParkingDynamicLinkPolicy` is immutable/versioned and bound to both the pinned static inventory manifest and the pinned dynamic manifest. `ParkingSourceBundle` requires it whenever a dynamic manifest is present.

V1 supports only:

`SHARED_CANONICAL_PARKING_ID`

The link policy also binds the existing canonical parking dynamic mapping profile ID/version. Under this V1 mode, the dynamic source's native `source_entity_id` must equal the canonical `parking_id`; otherwise canonical snapshot construction rejects the evidence. This prevents a provider-local entity from being arbitrarily reassigned to another static facility under the shared-ID mode.

Future cross-source linkage requires a separately versioned exact mapping artifact. Distance/name/geometry fuzzy matching remains out of scope.

The dynamic link-policy identity is included in `ParkingSourceBundle.identity`, therefore it propagates into parking measurement/snapshot identity. `ParkingDerivationEvidence` retains it explicitly as well.

## Verification

- provider tests: 418/418 PASS
- sitescore-data: 361/361 PASS
- sitescore-core: 86/86 PASS
- runtime dependency: `sitescore-data==0.1.0` only
- sitescore-core imports: 0
- changed non-parking production files vs original 3.3-8: 0
- CONTRACT_CHANGE_REQUIRED: 0
