# FAZ 3.4 — CHECKPOINT 3.4-2 COMMERCIAL EQUAL-AREA FRAME FOUNDATION

## Scope
This checkpoint introduces the provider-neutral structural benchmark-frame package `sitescore-benchmarks`. It depends only on locked `sitescore-spatial==0.1.0`. It does not implement metric measurement, benchmark distributions, ECDF, normalization, COMB-005, readiness, pipeline orchestration, provider acquisition, or core scoring.

## Structurally frozen decisions
- Canonical benchmark observation unit is always the **full equal-area lattice cell geometry**.
- Boundary overlap diagnostics never replace the full cell with a clipped fragment.
- Boundary membership is a separate policy/result semantic layer.
- Commercial population means `commercially_evidenced_spatial_alternatives` (v1.0).
- Commercial eligibility is tri-state: `ELIGIBLE`, `INELIGIBLE`, `UNKNOWN`.
- Absence of accepted positive evidence is not exclusion evidence and therefore does not imply `INELIGIBLE`.
- Actual structured evidence and actual immutable policies determine eligibility; caller-supplied eligibility claims are verified against evidence.
- Frame/cell/evidence identities are deterministic and content-bound; generated timestamps and replay locators are non-semantic.
- Cells are canonically ordered for frame identity, so enumeration/worker order is non-semantic.

## Explicitly unresolved production decisions
No values/rules were invented for:
- benchmark equal-area CRS selection;
- production cell resolution;
- lattice anchor/origin before CRS and resolution are approved;
- production boundary-membership method or overlap threshold;
- provider precedence or authority ranking;
- cross-provider reconciliation/deduplication;
- commercial-category empirical calibration;
- benchmark measurement coverage thresholds.

`EqualAreaProjectionPolicy`, `CellResolutionPolicy`, and `FrameBoundaryMembershipPolicy` explicitly represent unresolved state. A frame with unresolved lattice or membership semantics is `UNRESOLVED`; it is not converted to an empty frame, all-UNKNOWN population, or all-INELIGIBLE population.

## Projection and lattice contracts
`EqualAreaProjectionPolicy` binds policy id/version, explicit selection algorithm identity, resolution state, and an actual `CRSIdentity` only when resolved.

`CellResolutionPolicy` binds policy id/version and an explicit cell size/unit only when resolved. There is no default 100m/250m/500m/1km constant.

`LatticePolicy` binds:
- projection-policy identity;
- resolution-policy identity;
- cell shape;
- explicit anchor X/Y when fully resolved;
- axis alignment;
- indexing algorithm/version;
- actual `GeometryPrecisionPolicy`;
- actual `GeometryEngineIdentity`.

Changing selected CRS, resolution, anchor, indexing semantics, precision, or engine changes the lattice identity. No file path, timestamp, worker id, or iteration order participates.

## Full-cell preservation
`CommercialFrameCell.full_cell_geometry` is an actual hardened `sitescore-spatial.CanonicalGeometry` and remains the canonical observation geometry for interior, partial-overlap, tiny-overlap, boundary-touch, hole, and multipolygon interactions.

`BoundaryIntersectionEvidence` is diagnostic only. It can hold full-cell/boundary identities and optional diagnostic area/fraction/operation lineage. It never determines membership by itself. An unresolved diagnostic contains no fabricated zero values.

## Boundary membership
`FrameBoundaryMembership` carries the actual full-cell geometry, actual boundary artifact, actual membership policy, optional diagnostic evidence, derived/verified state and reason codes.

Because no production membership method is approved in this checkpoint, an unresolved policy yields `UNRESOLVED`. A structurally supplied future method identity is not silently implemented by this package; it remains unresolved until an approved evaluator exists. No centroid, representative-point, any-overlap, majority-overlap, 50% threshold, touching rule, or tiny-overlap rule is hidden in code.

## Commercial evidence
`EvidenceSourceIdentity` is provider-neutral. Its `content_hash` is explicitly a **declared immutable upstream content identity/reference**; this package does not own raw source bytes and therefore does not claim raw-byte verification. Replay/source locator remains non-semantic.

FRAME-H004/H005 split evidence semantics into actual immutable lineage objects:
- `CommercialEvidenceRecord`: provider-neutral raw/source evidence semantics.
- `CommercialEvidenceClassificationPolicy`: versioned classification-policy boundary. In Checkpoint 3.4-2 public `RESOLVED` construction is intentionally unavailable because no commercial ontology/category mapping has been approved.
- `CommercialEvidenceClassification`: derived/verified classification result. With the unresolved public policy it is necessarily `UNRESOLVED`; raw evidence cannot self-assert `POSITIVE` or `EXPLICIT_EXCLUSION`.
- `EvidenceCellApplicabilityPolicy`: versioned exact-cell applicability boundary. Public `RESOLVED` construction is intentionally unavailable because no point-in-cell/overlap/nearest/centroid/provider assignment rule is approved.
- `EvidenceCellApplicability`: actual relationship between one classification artifact and one exact `LatticeCellArtifact`.
- `CommercialEvidenceItem`: binds the classification and exact-cell applicability artifacts.
- `CommercialFrameEvidenceBundle`: carries the actual target `LatticeCellArtifact` plus canonical evidence items. `cell_lattice_id` is derived only from that actual object.

No Overture, Google, Census/TIGER, OSM, parcel-provider, or municipal schema is encoded in canonical contracts. Source identity alone proves neither commercial classification nor spatial applicability.

## Commercial eligibility
`CommercialEvidencePolicy` retains provider-neutral accepted positive/exclusion class sets and structural UNKNOWN behavior for conflict/insufficient evidence. `CommercialEligibilityResult` carries the actual bundle and actual policy and recomputes state/reasons.

The evaluator only counts an evidence item if **both** conditions hold:
1. classification is resolved to `POSITIVE` or `EXPLICIT_EXCLUSION` under an actual classification-policy artifact; and
2. applicability state is `APPLICABLE` to the exact target lattice cell.

Unresolved classification or unresolved applicability cannot yield `ELIGIBLE` or `INELIGIBLE`. Mere record existence, missing records, or absence of qualifying positive evidence remains `UNKNOWN`. Since 3.4-2 intentionally leaves both classification and applicability execution rules unresolved, normal public production evidence remains UNKNOWN until later approved policies exist. White-box tests use non-public synthetic resolved policy objects only to verify downstream evaluator gating; they do not expose a production ontology or spatial-assignment rule.

## Frame identity
`CommercialFrame.frame_id` commits to:
- benchmark geography identity;
- boundary artifact identity;
- lattice policy identity;
- membership policy identity;
- eligibility policy identity;
- canonical ordered cell identities;
- frame population definition/version;
- derived frame state/reasons.

Each cell identity commits to the full-cell canonical geometry, lattice/index identity, full area/unit, boundary-membership identity, commercial evidence-bundle identity, eligibility identity, and canonical source references.

`generated_at` does not affect frame identity.

## Future benchmark measurement completeness invariant
No benchmark measurement is implemented here. Later measurement/distribution construction must audit against the explicit complete eligible frame-cell population. An eligible frame cell with missing/unresolved measurement must not silently disappear. No minimum-N, minimum-coverage percentage, or omission rule is introduced in 3.4-2.

## Tests
Checkpoint suite covers deterministic ordering, generated-at non-semanticity, full-cell preservation across overlap cases, unresolved membership, lattice identity sensitivity, tri-state evidence semantics, anti-self-assertion, provider neutrality, evidence-source content binding, and scope/import boundaries.

## Frozen dependency verification
Locked `sitescore-spatial` remains unmodified and is verified separately at 180/180 PASS with SHA-256 `0ce9b471a84f39fc663cb54f2d4ef437b2c1d205c62b55137892f2eb6499d0bb`.
Frozen core/data/providers are also re-run independently and authoritative hashes are unchanged.

## CONTRACT_CHANGE_REQUIRED
`0` — the structural frame foundation is representable through new sidecar contracts without changing frozen core/data/providers or locked spatial semantics.

---

# FRAME-H001–H003 HARDENING RECORD

## FRAME-H001 — equal-area attestation

Checkpoint 3.4-2 intentionally does **not** define a production equal-area CRS attestation mechanism. `EqualAreaProjectionPolicy.state=RESOLVED` is therefore not a constructible public production-semantic state in this checkpoint. An unresolved policy carries no selected CRS.

Consequences:

- EPSG:3857 is not accepted as equal-area.
- EPSG:3395 is not accepted as equal-area.
- Being projected and metre-based is not treated as proof of equal-area behavior.
- No production CRS constant or projection-method registry is introduced merely to unlock frame generation.

A later checkpoint/review must approve an executable, versioned equal-area attestation/selection policy before the `RESOLVED` state can become production-usable.

## FRAME-H002 — lattice-cell derivation boundary

Canonical frame cells no longer accept independently supplied lattice policy/index/geometry/area/unit fields.

`CommercialFrameCell` now requires an actual `LatticeCellArtifact`. The lattice artifact binds:

- actual `LatticePolicy`;
- integer lattice indices `(i,j)`;
- full `CanonicalGeometry`;
- successful spatial `AREA` result for that exact geometry;
- derivation algorithm/version.

Its contract verifies the selected lattice CRS, spatial canonicalization policy, engine lineage, square bounds implied by anchor + resolution + integer index, exact square corner set, geometry area, and AREA-result value/unit.

Because FRAME-H001 leaves equal-area projection unresolved, public canonical lattice-cell generation is intentionally unavailable in Checkpoint 3.4-2. `derive_lattice_cell()` rejects unresolved lattices. The valid structural production frame is therefore allowed to be unresolved with zero canonical cells rather than manufacturing arbitrary fixture polygons as equal-area observations.

The regression suite uses a white-box test-only synthetic resolved policy solely to exercise downstream derivation invariants (foreign CRS, wrong size/location/index, area derivation). This test bypass is not exposed through the production construction API and does not designate any CRS as an approved equal-area production CRS.

## FRAME-H003 — geography/boundary/diagnostic evidence coherence

### Frame geography and boundary

`CommercialFrame` requires:

`boundary_artifact.geography_identity.identity_id == benchmark_geography.identity_id`.

A frame cannot claim one geography while using another geography's boundary artifact.

### Frame cells and frame boundary

For every canonical frame cell, the frame verifies that the cell membership result uses the exact frame boundary artifact and the exact full lattice-cell geometry.

### Boundary diagnostic coherence

`BoundaryIntersectionEvidence.intersection_fraction` is no longer caller-controlled. It is a derived property:

`intersection_area / full_cell_area`.

For AVAILABLE evidence, area values must be finite, `intersection_area >= 0`, `full_cell_area > 0`, and `intersection_area <= full_cell_area`.

If an `intersection_operation` is attached, it must be an actual locked-spatial `INTERSECT` operation whose canonical-sorted input semantic geometry IDs are exactly:

- the attached full-cell geometry; and
- the attached boundary artifact's canonical geometry.

The diagnostic area floats are explicitly numeric diagnostic evidence; the INTERSECT result itself does not attest their area calculation. A future design that needs execution-attested diagnostic area lineage must attach actual AREA operation results rather than treating these floats as if INTERSECT computed area.

`FrameBoundaryMembership` additionally requires any attached diagnostic to refer to the same full-cell geometry and same boundary artifact as the membership result.

None of these diagnostics determine MEMBER/NON_MEMBER while the membership policy remains unresolved.

## Hardened regression baseline

- `sitescore-benchmarks`: 52/52 PASS
- locked `sitescore-spatial`: 180/180 PASS
- frozen `sitescore-core`: 86/86 PASS
- frozen `sitescore-data`: 361/361 PASS
- frozen `sitescore-providers`: 418/418 PASS

Locked/frozen artifact hashes remain unchanged.

## Hardening unresolved decisions

Still unresolved by design:

- approved equal-area CRS attestation/selection mechanism;
- selected equal-area CRS;
- production cell resolution;
- production lattice anchor/origin;
- boundary-membership method/threshold semantics;
- provider precedence/reconciliation;
- benchmark measurement coverage rules.

`CONTRACT_CHANGE_REQUIRED = 0`.

---

# FRAME-H004/H005 + ARTIFACT-H001 EVIDENCE-LINEAGE HARDENING RECORD

## FRAME-H004 — actual cell-target lineage
`CommercialFrameEvidenceBundle` no longer accepts a detached `cell_lattice_id` string. It requires the actual immutable `LatticeCellArtifact`; `cell_lattice_id` is a derived property. Every attached evidence item must carry an `EvidenceCellApplicability` targeting that same exact lattice-cell semantic identity. `CommercialEligibilityResult` remains transitively attached to the target cell through its actual evidence bundle.

## FRAME-H005 — classification and applicability lineage
Caller-controlled disposition was removed from raw evidence. Classification and exact-cell applicability are separate actual immutable artifacts with explicit policies. Because no production commercial ontology or cell-assignment method is approved in Checkpoint 3.4-2, both public policy families only admit `UNRESOLVED`; arbitrary POSITIVE/EXPLICIT_EXCLUSION/APPLICABLE claims are rejected by their constructors. Eligibility counts evidence only when classification is resolved and applicability is APPLICABLE to the bundle's exact target cell. Thus source-record existence alone cannot create eligibility, and absence remains UNKNOWN.

Policy/version changes alter classification/applicability item identity and transitively bundle/result identity. Target-cell changes likewise alter bundle/result identity. No opaque composite attestation hash is introduced.

## ARTIFACT-H001 — clean freeze artifact
The final ZIP is generated from a clean source tree after tests. `.pytest_cache/`, `__pycache__/`, `*.pyc`, `*.pyo`, machine-local build/temp noise are excluded. ZIP entries are sorted and written with deterministic timestamps/permissions before SHA-256 is calculated.

## Evidence-lineage hardened baseline
- `sitescore-benchmarks`: 63/63 PASS
- locked `sitescore-spatial`: 180/180 PASS
- frozen `sitescore-core`: 86/86 PASS
- frozen `sitescore-data`: 361/361 PASS
- frozen `sitescore-providers`: 418/418 PASS

`CONTRACT_CHANGE_REQUIRED = 0`.
