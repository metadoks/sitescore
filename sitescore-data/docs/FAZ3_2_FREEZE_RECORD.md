# FAZ 3.2 Contract Architecture Freeze Record

## Status

**FAZ 3.2 CONTRACT ARCHITECTURE — FROZEN**

This record freezes the typed real-data contract architecture implemented in `sitescore-data` v0.1.0. It does not freeze provider implementations, normalization/calibration algorithms, application-layer aggregation, or core integration.

## Frozen baseline

- Package: `sitescore-data`
- Package version: `0.1.0`
- Test baseline: **361/361 PASS**
- Runtime dependencies: `[]`
- `sitescore_data` MUST NOT import `sitescore` / `sitescore-core`
- Provider libraries/imports in the frozen contract package: none
- Circular internal dependencies: none

## Checkpoint lock state

- Checkpoint 1 — Foundation: **LOCKED**
- Checkpoint 2 — Common Schemas: **LOCKED**
- Checkpoint 3 — Domain Snapshots I: **LOCKED**
- Checkpoint 4 — Domain Snapshots II: **LOCKED**
- Checkpoint 5 — Feature Contracts: **LOCKED**
- Checkpoint 6 — Scoring Readiness Boundary: **LOCKED**
- Checkpoint 7 — Pipeline Result Contract: **LOCKED**

## Final architecture audit decision

The final architecture and invariant audit initially returned:

`B) READY AFTER 4 SMALL FIXES`

The required freeze fixes were then applied and verified. Final decision:

**FAZ 3.2 CONTRACT ARCHITECTURE — READY TO FREEZE**

This freeze record marks that architecture as **FROZEN**.

## Final freeze fixes

1. **Site evidence → normalized feature → benchmark identity binding**
   - Transit site `source_bundle_fingerprint` is bound to normalized transit feature metadata at the pipeline boundary.
   - Competition site `measurement_definition_id` is bound to normalized competition feature metadata at the pipeline boundary.
   - Existing readiness compatibility checks continue to bind normalized feature identity to benchmark identity.

2. **ScoringReadinessResult structural hardening**
   - Canonical V1 readiness contains exactly the frozen eight normalized features in deterministic order.
   - Every canonical V1 readiness feature is required.
   - Blocking summary collections and machine reason codes are structurally consistent with feature states.
   - Fabricated empty `is_score_ready=True` results are rejected.

3. **Equal-area commercial benchmark marker**
   - Canonical commercial benchmark frame metadata explicitly carries `SpatialRepresentation.EQUAL_AREA`.
   - Projection/tessellation metadata remain descriptive; no geospatial calculation engine is part of this contract layer.

4. **Feature-contract version coherence**
   - Within one canonical pipeline object graph, derived metrics, normalized features, and pipeline `DataContractVersions` must use the same data feature contract version.
   - Historical coherent versions remain representable; equality to the current package constant is not required.

5. **Provenance semantic clarification**
   - `source_ref` / `source_refs` are opaque provenance identities.
   - They are **not** universally guaranteed to resolve to `SourceMetadata.source_id`.
   - `SourceMetadata` is a metadata registry for source identities known/available to a result, not a universal registry for all artifact/reference namespaces.
   - Typed provenance namespaces such as `SourceRef` / `ArtifactRef` may be introduced only in a future contract-major revision.

## Frozen ownership boundary

Canonical ownership remains:

```text
sitescore-core/   # frozen scoring/financial core v0.1.0
sitescore-data/   # frozen real-data contract architecture v0.1.0
sitescore-app/    # future integration/application boundary
```

Data-layer flow ends at:

```text
provider/builders (future)
    -> frozen sitescore-data contracts
    -> normalization/calibration (future)
    -> ScoringReadinessValidator
    -> RealDataPipelineResult(SCORE_READY)
```

`SCORE_READY` means downstream category aggregation/scoring is permitted. It does **not** mean category scores have already been computed.

Future app-layer ownership remains:

```text
RealDataPipelineResult(SCORE_READY)
    -> sitescore-app category aggregation using frozen core configuration
    -> readiness-gated ReadyCategoryScorePayload
    -> core CategoryScores adapter
    -> sitescore-core analyze()
```

`sitescore-data` does not own category aggregation and does not import the frozen core.

## Deferred by design — not guarantees of the frozen contract

The following are intentionally **not implemented or guaranteed** by this freeze:

1. **Canonical readiness fingerprint generation**
   - `readiness_fingerprint` remains a caller-supplied deterministic external identity/reference.
   - It is not guaranteed to be cryptographic or content-bound.

2. **`SourceMetadata.content_hash` canonical grammar**
   - The field remains an explicit non-empty opaque value.
   - No mandatory `algorithm:digest` grammar is frozen yet.

3. **TransitSourceBundle fingerprint generation**
   - Equality/identity semantics are frozen where consumed.
   - The algorithm that constructs the fingerprint is deferred to provider/artifact implementation.

4. **Canonical JSON / artifact fingerprinting**
   - `to_primitive()` provides deterministic primitive serialization.
   - Canonical JSON byte encoding and cryptographic artifact hashing are not part of this freeze.

5. **Typed provenance identity namespaces**
   - `SourceRef`, `ArtifactRef`, and similar value-object namespaces are deferred to a future contract-major revision if needed.

6. **ReadyCategoryScorePayload app-boundary version binding**
   - The payload remains a boundary DTO.
   - Its `feature_contract_version` must later be bound to the app-layer aggregation input/result contract; it is not part of `RealDataPipelineResult`.

7. **Provider connectors and builders**
   - Census, routing, GTFS, competition/benchmark, parking, and other provider implementations are not frozen by this record because they are not implemented in FAZ 3.2.

8. **Empirical calibration and validation**
   - Benchmark resolution tolerance, normalization calibration, COMB-005 calibration, empirical model validation, and related production calibration remain pending.

## Freeze identity

- Package version remains `0.1.0`.
- The freeze identity is recorded by the Git tag `sitescore-data-v0.1.0` on the freeze commit.
- No additional schema field or package-version bump is introduced solely for the freeze.
