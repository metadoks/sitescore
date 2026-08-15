# FAZ 3.4 — Checkpoint 3.4-1 Spatial Foundation

## Status

Checkpoint implementation complete and ready for adversarial review. No Checkpoint 3.4-2 implementation is included.

`CONTRACT_CHANGE_REQUIRED = 0`

Frozen `sitescore-core`, `sitescore-data`, and `sitescore-providers` were not modified.

## Package ownership / DAG

```text
sitescore-spatial
  -> shapely==2.1.2
  -> pyproj==3.7.2
```

The package has zero imports from any SiteScore domain package. It owns deterministic geometry/CRS operations and immutable spatial sidecar contracts only.

## Dependency decision

Direct pins:

- Shapely `2.1.2` — BSD-3-Clause; Python >=3.10; NumPy >=1.21; GEOS >=3.9.
- pyproj `3.7.2` — MIT; Python >=3.11; runtime dependency `certifi`; PROJ-backed CRS/transformation engine.

Reference environment used for this checkpoint:

- Python `3.13.5`
- Shapely `2.1.2`
- GEOS `3.13.1`
- pyproj `3.7.2`
- PROJ `9.5.1`
- NumPy `2.3.5`
- certifi `2026.5.20`
- `proj.db` SHA-256 `a25d85a2ebfc4584eba65186b7c41743b084ce5d391941cbb41c805947b77109`

Reference environment dependency lock is recorded in `requirements.lock`. Package runtime dependencies remain only Shapely and pyproj.

Official verification sources:

- https://pypi.org/project/shapely/2.1.2/
- https://shapely.readthedocs.io/en/2.1.2/reference/shapely.normalize.html
- https://shapely.readthedocs.io/en/2.1.2/reference/shapely.to_wkb.html
- https://pypi.org/project/pyproj/3.7.2/
- https://pyproj4.github.io/pyproj/stable/api/transformer.html
- https://pyproj4.github.io/pyproj/stable/transformation_grids.html
- https://libgeos.org/
- https://proj.org/en/stable/about.html

No GeoPandas/Pandas/H3/DuckDB/PostGIS/Rasterio/Fiona dependency was added.

## Deterministic runtime policy

- Canonical transform operations force PROJ network access disabled.
- Ballpark transforms are forbidden by V1 transform policy.
- `always_xy=True` is explicit and version-bound; authority-axis defaults are not hidden.
- `TransformerGroup.best_available` is required by the default policy.
- Missing best transformation/grid material produces `UNRESOLVED`, never a silent approximate replacement.
- Selected grid identities are content-hashed when local grid bytes are deterministically observable. If a selected available grid cannot be content-identified, transform planning returns unresolved.
- `GeometryEngineIdentity` binds Python, Shapely, GEOS, pyproj, PROJ and `proj.db` content identity; machine paths/hostnames are excluded.

## Independent identity grammar

Grammar:

```text
sitescore-spatial-canonical-json / 1.0
hash = SHA-256
```

Properties:

- explicit primitive type tags;
- bool != int != float;
- finite floats only;
- float identity uses exact `float.hex()` representation;
- non-string mapping keys reject;
- mapping keys canonical-sort;
- set/frozenset values canonical-sort;
- unsupported objects reject;
- storage locator/retrieval noise is excluded by contract-specific semantic preimages.

## CRS identity model

`CRSIdentity` binds:

- authority + code where available;
- canonical PROJJSON definition hash;
- axis name/direction/unit/conversion-factor semantics;
- geographic/projected classification;
- CRS definition policy id/version.

A free-form `"EPSG:4326"` label is not itself the CRS semantic identity.

## Geometry source identity

`GeometrySourceIdentity` binds:

- provider;
- dataset;
- exact immutable release;
- vintage;
- schema version;
- source CRS identity;
- raw content SHA-256.

Mutable `latest/current/live/today/now` release-style identities reject. A declared raw hash is validated against actual bytes. File path/URI is not part of source semantic identity.

## Geometry canonicalization

V1 boundary policy:

- Polygon + MultiPolygon only;
- strict 2D only;
- non-finite coordinates reject;
- empty boundary geometry rejects;
- invalid geometry rejects;
- no repair;
- Shapely strict `normalize()` canonicalizes coordinate/ring/multi-part ordering;
- canonical encoding is OGC WKB, little-endian, 2D, no SRID;
- no coordinate quantization is introduced: `GeometryPrecisionPolicy = FULL_DOUBLE / 1.0`.

Canonicalization and repair are separate concepts. No repair policy exists in this checkpoint.

## BoundaryGeometryArtifact

Immutable sidecar binds:

- structured `GeographyIdentity`;
- geometry role;
- `GeometrySourceIdentity`;
- canonical geometry hash/type/CRS;
- parser id/version;
- canonicalization policy identity;
- engine identity;
- source refs.

`raw_artifact_ref` and `generated_at` are provenance only and are excluded from `geometry_artifact_id`.

Distinctions preserved:

```text
raw content identity
!= source/parsed derivation identity
!= canonical geometry identity
!= replay/storage locator
```

## GeographyGeometryCompatibility

Compatibility is not self-asserted. The evaluator receives and validates:

- actual adapter-side geography identity;
- actual demographic/geography definition identity;
- actual attached `BoundaryGeometryArtifact`;
- separate trusted deployment compatibility policy.

It verifies geography type, canonical identifier, actual demographic definition, actual geometry definition and trusted policy expectations before emitting `COMPATIBLE`.

Same geography identifier with incompatible vintage/definition returns `INCOMPATIBLE`.

## CRS transform semantics

Default `CRSTransformPolicy`:

```text
axis_order_policy = ALWAYS_XY
allow_ballpark = false
require_best_available = true
network_enabled = false
```

Transform semantic identity binds:

- source CRS;
- target CRS;
- transform policy;
- selected operation/pipeline identity;
- selected grid identity when used;
- engine identity.

A source/target CRS change or transform policy-version change changes operation identity.

## Operation/result model

Implemented operations:

- canonicalization;
- projection;
- polygon/multipolygon intersection;
- projected planar area.

Result states:

```text
SUCCESS
UNRESOLVED
INVALID_INPUT
INCOMPATIBLE
ENGINE_ERROR
```

Spatial failures never become zero area/empty negative site evidence.

Intersection semantic input order is canonicalized, so `A ∩ B` and `B ∩ A` have identical operation identity/results when semantics match.

A valid empty intersection may be represented only when the explicit operation policy allows it; this is not a provider/site zero claim.

## Area semantics

Area uses planar GEOS area only on an explicitly supplied projected CRS whose first two axes are metres.

Geographic CRS area (`degrees²`) is structurally rejected as `INCOMPATIBLE`.

No default equal-area CRS is selected in 3.4-1. Caller must explicitly supply/produce an approved projected CRS in future work.

## Precision boundary

Spatial coordinate precision is separate from future measurement/ECDF precision.

3.4-1 freezes only:

```text
GeometryPrecisionPolicy:
  FULL_DOUBLE / 1.0
  grid_size = None
```

No rounding grid is invented. `MeasurementPrecisionPolicy` and ECDF tie quantization remain deferred to later checkpoints.

## Test baseline

`sitescore-spatial`: **59/59 PASS**.

Covered regression classes include:

- identity grammar/type separation;
- source/release/vintage/raw-content sensitivity;
- storage-path and generated-time non-sensitivity;
- CRS and engine identity;
- ring start/orientation invariance;
- multipolygon ordering invariance;
- GeoJSON key-order invariance;
- invalid/empty/Z/non-finite rejection;
- geography definition/vintage compatibility;
- foreign artifact rejection;
- commutative intersection identity;
- empty intersection state semantics;
- CRS mismatch;
- explicit transform policy;
- lat/lon out-of-range swap failure;
- WGS84 area shortcut rejection;
- area policy identity sensitivity;
- explicit engine-failure state;
- forbidden dependency/import audit.

## Frozen repository verification

Re-extracted from authoritative ZIPs and executed without modifying source:

```text
sitescore-core      86/86 PASS
sitescore-data     361/361 PASS
sitescore-providers 418/418 PASS
```

Authoritative ZIP SHA-256 after checkpoint work:

```text
core      aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192
data      386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b
providers f45d6843c65025ec60269e3c62f852b8bc23bef731d54af8472288ef4ba72ee2
```

Frozen production source changes: `core=0`, `data=0`, `providers=0` (checkpoint work occurred only in the new sibling tree).

## Explicitly deferred

- actual boundary provider (TIGER/Line or alternative);
- benchmark equal-area CRS;
- benchmark cell resolution;
- frame boundary-membership rule;
- population allocation policy;
- target age definition;
- competition scalar reduction;
- road scalar reduction;
- measurement numeric quantization / ECDF precision;
- COMB-005 formula/weights.

No benchmark/frame/metric/normalization/readiness/pipeline implementation is included.

---

# Checkpoint 3.4-1 Spatial Foundation Hardening

Hardening input: `FAZ3_4_CHECKPOINT_3_4_1_SPATIAL_HARDENING_PROMPT.md`.

## SPATIAL-H001 — content-bound public identities

Hardened public identity-bearing immutable records now recompute and enforce their semantic identities from their own semantic fields where sufficient information is present:

- `CRSIdentity.crs_identity_id`
- `GeometrySourceIdentity.source_identity_id`
- `GeometryEngineIdentity.engine_identity_id`
- `CanonicalGeometry.canonical_geometry_hash` and `semantic_geometry_id`
- `BoundaryGeometryArtifact.geometry_artifact_id`
- `GeographyGeometryCompatibility.compatibility_id`
- `TransformPlan.selected_pipeline_hash` and `plan_id`
- `GeometryOperationResult.operation_id`

`CanonicalGeometry` additionally decodes its WKB and verifies geometry family, empty state, and V1 2D semantics.

Real geometry/projection execution calls attest the supplied `GeometryEngineIdentity` against the actual installed runtime returned by `build_geometry_engine_identity()`. An internally self-consistent fictional engine record cannot attest Shapely/GEOS/pyproj/PROJ computation.

`GeometryOperationResult` now enforces state/payload invariants: successful geometry operations require geometry output only; successful AREA requires numeric value + unit only; non-success states cannot carry success payloads.

## SPATIAL-H002 — output semantic geometry binding

Geometry-producing operation result identity now commits to `output_geometry.semantic_geometry_id`, not only WKB/content hash. Therefore canonicalization policy, CRS identity, engine identity, geometry type, and canonical bytes are transitively bound to the operation identity.

Intersection input semantic IDs remain canonical-sorted, preserving `A ∩ B == B ∩ A` identity under identical semantics.

## SPATIAL-H003 — one-shot transform resolution/execution

`resolve_transform_plan()` now selects the transform once and returns:

```text
immutable TransformPlan
+
exact runtime Transformer
```

`project_geometry()` executes that exact Transformer object. It does not instantiate a second `TransformerGroup` or independently select another operation.

`transformer_from_plan()` remains a strict replay helper: if the exact stored pipeline cannot be replayed and revalidated against the plan hash/grid identities, it returns no transformer; there is no generic source→target fallback.

## Coordinate-order clarification

V1 defines explicit `ALWAYS_XY` semantics. Out-of-domain coordinates can be rejected by the transform engine under `errcheck=True`, but generic spatial code cannot universally infer that two numerically plausible longitude/latitude values were caller-swapped. Plausible coordinate-role mistakes require upstream typed provenance/validation.

## Hardening regression baseline

```text
sitescore-spatial = 77/77 PASS
```

New adversarial coverage includes forged identity IDs, fictional self-consistent runtime identities, WKB/hash/type mismatch, artifact/plan/result ID mismatch, result state/payload fabrication, output-policy operation identity sensitivity, one-shot resolver execution, and no exact-replay fallback.

## Frozen repository verification after hardening

```text
sitescore-core       86/86 PASS
SHA-256 aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192

sitescore-data       361/361 PASS
SHA-256 386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b

sitescore-providers  418/418 PASS
SHA-256 f45d6843c65025ec60269e3c62f852b8bc23bef731d54af8472288ef4ba72ee2
```

Production changes were confined to `sitescore-spatial`. SiteScore-domain imports from spatial remain zero. No benchmark, metric, normalization, COMB-005, readiness, or pipeline implementation was introduced.

`CONTRACT_CHANGE_REQUIRED = 0`.

---

## Final hardening — SPATIAL-H004 / SPATIAL-H005

### SPATIAL-H004 — CanonicalGeometry canonicality proof

Status: **RESOLVED**.

`CanonicalGeometry` now carries the actual immutable `GeometryCanonicalizationPolicy`, not only a detached policy hash. Direct construction re-decodes stored WKB and re-runs the exact V1 canonical-byte pipeline (supported Polygon/MultiPolygon family, 2D, finite coordinates, validity/no repair, explicit empty behavior, `shapely.normalize()`, OGC ISO WKB little-endian 2D no SRID). The resulting bytes must match `canonical_wkb` byte-for-byte.

`EmptyGeometryBehavior` now distinguishes:

- `REJECT` — boundary/default canonical geometry semantics;
- `ALLOW_OPERATION_OUTPUT` — explicit canonical semantics for legitimate empty spatial-operation outputs.

The former hidden `allow_empty=True` override was removed. `intersect_geometries()` uses an explicit operation-output canonicalization policy only when an allowed empty intersection is actually emitted, and that policy identity is bound into `CanonicalGeometry.semantic_geometry_id`.

`BoundaryGeometryArtifact` now carries the actual `CanonicalGeometry` and validates its hash/type/CRS/policy/engine coherence. Empty canonical geometry is rejected at the public artifact constructor as well as the builder boundary.

Regressions include self-consistent but non-normalized Polygon WKB, MultiPolygon member-order noise, exact canonical direct reconstruction, empty-policy mismatch, explicit empty operation-output policy identity, and direct empty boundary artifact rejection.

### SPATIAL-H005 — PROJECT transform-plan lineage

Status: **RESOLVED**.

`GeometryOperationResult` now carries the actual immutable `TransformPlan | None`, with `transform_plan_id` exposed only as a derived property. PROJECT results additionally bind `input_crs_identity_id`.

Constructor invariants:

- `SUCCESS + PROJECT` requires an attached exact `TransformPlan`;
- attached plan engine identity must equal result engine identity;
- plan source CRS identity must equal result input CRS identity;
- successful PROJECT output CRS must equal plan target CRS identity;
- INTERSECT / AREA / CANONICALIZE must not carry transform plans;
- non-success PROJECT may omit a plan if resolution failed before selection, or preserve the resolved plan when execution failed after selection.

Operation identity commits to the attached plan's derived `plan_id` and the input CRS identity. A detached arbitrary transform-plan hash is no longer accepted as lineage proof.

`project_geometry()` preserves the plan returned by the one-shot resolver in both successful results and post-resolution execution failures. The same resolved runtime Transformer remains the execution object; no generic re-selection fallback was introduced.

Regressions include missing plan, foreign-source plan, engine mismatch, output-target CRS mismatch, plan injection into INTERSECT/AREA, official exact-plan emission, and deterministic repeated PROJECT identity.

### Final regression baseline

```text
sitescore-spatial = 92/92 PASS
```

### Frozen dependency baselines reverified

```text
sitescore-core       = 86/86 PASS
sitescore-data       = 361/361 PASS
sitescore-providers  = 418/418 PASS
```

Authoritative frozen ZIP SHA-256 values remain:

```text
sitescore-core
  aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192

sitescore-data
  386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b

sitescore-providers
  f45d6843c65025ec60269e3c62f852b8bc23bef731d54af8472288ef4ba72ee2
```

### Final scope / dependency audit

```text
SiteScore-domain imports from sitescore-spatial = 0
new unintended runtime dependencies             = 0
benchmark/frame implementation                   = 0
metric implementation                            = 0
ECDF/normalization                               = 0
pipeline/readiness                               = 0
Checkpoint 3.4-2 implementation                  = 0
CONTRACT_CHANGE_REQUIRED                         = 0
```

---

# Policy-Lineage Hardening — SPATIAL-H006

Status: RESOLVED.

## SPATIAL-H006-A — GeometryOperationResult policy lineage

The public result contract no longer accepts a detached caller-controlled `operation_policy_id` field. It now carries the actual immutable `GeometryOperationPolicy` object as `operation_policy`; `operation_policy_id` is a derived property.

Constructor invariants enforce:

- `operation_policy.operation == result.operation`;
- `CANONICALIZE`, `INTERSECT`, and `PROJECT` must not carry `AreaPolicy`;
- successful empty `INTERSECT` requires `operation_policy.allow_empty_result=True`;
- `AREA` carries the actual immutable `AreaPolicy` plus the actual input `CRSIdentity`;
- successful `AREA` requires a projected, metre-based CRS;
- successful `AREA` unit must equal `AreaPolicy.output_unit`;
- non-AREA results cannot carry `AreaPolicy`;
- AREA results cannot carry a transform plan.

The previous opaque AREA composite hash is removed. AREA operation identity now commits explicitly to:

```text
operation
input semantic geometry IDs
GeometryOperationPolicy.identity_id
AreaPolicy.identity_id
input CRS identity
engine identity
numeric value
unit
state
reason codes
```

Official execution paths attach the exact policy objects passed to the operation.

## SPATIAL-H006-B — TransformPlan policy lineage

The public `TransformPlan` contract no longer accepts a detached caller-controlled `policy_identity_id` field. It carries the actual immutable `CRSTransformPolicy` as `transform_policy`; `policy_identity_id` is derived from `transform_policy.identity_id`.

Plan identity is recomputed from:

```text
source CRS identity
target CRS identity
actual CRSTransformPolicy.identity_id
engine identity
selected pipeline hash
canonical grid identities
```

`resolve_transform_plan()` attaches the exact policy object used to create the `TransformerGroup`. The existing one-shot plan+Transformer resolution/execution behavior is preserved. Strict replay remains exact-pipeline only and does not fall back to generic CRS reselection.

## Policy-lineage regressions

Added regressions cover:

- detached `operation_policy_id` constructor input is impossible;
- INTERSECT result + PROJECT policy rejects;
- PROJECT result + INTERSECT policy rejects;
- AREA result + non-AREA policy rejects;
- successful empty INTERSECT with `allow_empty_result=False` rejects;
- successful empty INTERSECT with `allow_empty_result=True` succeeds and retains the exact policy;
- successful AREA without AreaPolicy rejects;
- successful AREA without input CRS rejects;
- AREA output unit mismatch rejects;
- successful AREA under geographic CRS rejects;
- official AREA result retains exact GeometryOperationPolicy, AreaPolicy, and input CRS;
- detached TransformPlan `policy_identity_id` constructor input is impossible;
- same transform pipeline with different transform-policy version produces different plan identity;
- official PROJECT result retains the exact CRSTransformPolicy and GeometryOperationPolicy;
- operation policy version changes operation result identity;
- all prior H001–H005 regression guarantees remain green.

Final spatial baseline after H006:

```text
sitescore-spatial = 107/107 PASS
```

Frozen verification:

```text
sitescore-core      = 86/86 PASS
sitescore-data      = 361/361 PASS
sitescore-providers = 418/418 PASS
```

Authoritative frozen ZIP SHA-256 values remain unchanged:

```text
sitescore-core
aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192

sitescore-data
386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b

sitescore-providers
f45d6843c65025ec60269e3c62f852b8bc23bef731d54af8472288ef4ba72ee2
```

Dependency/import/scope audit remains clean:

```text
SiteScore domain imports from sitescore-spatial = 0
new runtime dependencies = 0
Checkpoint 3.4-2 implementation = 0
CONTRACT_CHANGE_REQUIRED = 0
```

---

# Precision-Lineage Hardening — SPATIAL-H007

Status: RESOLVED.

## GeometryOperationPolicy precision lineage

The public `GeometryOperationPolicy` contract no longer accepts a detached caller-controlled `precision_policy_id`. It now carries the actual immutable `GeometryPrecisionPolicy` as `precision_policy`; `precision_policy_id` is a derived property.

Operation-policy identity commits to:

```text
policy_id
policy_version
operation
actual GeometryPrecisionPolicy.identity_id
allow_empty_result
```

No detached precision hash can attest operation semantics.

## Geometry-producing execution coherence

For `INTERSECT` and `PROJECT`, execution rejects before successful computation unless:

```text
GeometryOperationPolicy.precision_policy.identity_id
==
GeometryCanonicalizationPolicy.precision_policy.identity_id
```

Successful public geometry-producing results (`CANONICALIZE`, `INTERSECT`, `PROJECT`) independently enforce:

```text
result.operation_policy.precision_policy.identity_id
==
result.output_geometry.canonicalization_policy.precision_policy.identity_id
```

Legitimate empty intersection output continues to use the explicit `ALLOW_OPERATION_OUTPUT` canonicalization mode while preserving the exact same `GeometryPrecisionPolicy` identity.

## AREA precision lineage

AREA does not perform a new canonicalization step; it measures an already canonical geometry. V1 therefore freezes the structural rule:

```text
AREA GeometryOperationPolicy.precision_policy
==
measured CanonicalGeometry.canonicalization_policy.precision_policy
```

To make this invariant public and constructor-verifiable, `GeometryOperationResult` now carries the actual immutable `input_geometry_precision_policy` for AREA results. The result constructor requires it and verifies exact identity equality with the attached operation policy precision.

AREA result identity explicitly commits to `input_geometry_precision_policy.identity_id`; no opaque composite precision hash is introduced.

Official `area_of_projected_geometry()` passes the exact precision policy from the measured `CanonicalGeometry` into the result lineage.

## H007 regressions

Added regressions cover:

- detached `precision_policy_id` constructor input is impossible;
- changing the actual GeometryPrecisionPolicy changes GeometryOperationPolicy identity;
- INTERSECT operation/canonicalization precision mismatch rejects;
- same-precision INTERSECT remains successful;
- empty INTERSECT preserves precision identity under `ALLOW_OPERATION_OUTPUT`;
- PROJECT operation/canonicalization precision mismatch rejects;
- official PROJECT result precision equals output canonical geometry precision;
- public successful geometry result with operation/output precision mismatch rejects;
- AREA operation precision inconsistent with measured geometry precision rejects before execution;
- public AREA result with foreign input precision evidence rejects;
- official AREA result retains exact measured input precision policy;
- GeometryPrecisionPolicy change changes AREA operation/result identity;
- all prior H001–H006 guarantees remain green.

Final spatial baseline after H007:

```text
sitescore-spatial = 119/119 PASS
```

Frozen verification:

```text
sitescore-core      = 86/86 PASS
sitescore-data      = 361/361 PASS
sitescore-providers = 418/418 PASS
```

Authoritative frozen ZIP SHA-256 values remain unchanged:

```text
sitescore-core
aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192

sitescore-data
386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b

sitescore-providers
f45d6843c65025ec60269e3c62f852b8bc23bef731d54af8472288ef4ba72ee2
```

Dependency/import/scope audit remains clean:

```text
SiteScore domain imports from sitescore-spatial = 0
new runtime dependencies = 0
Checkpoint 3.4-2 implementation = 0
CONTRACT_CHANGE_REQUIRED = 0
```

---

# Execution-Attestation Hardening — SPATIAL-H008 / SPATIAL-H009

Status: RESOLVED.

## SPATIAL-H008 — executable CRS semantics

`CRSIdentity` no longer accepts a detached caller-controlled `canonical_definition_hash` as the only proof of CRS meaning. The public immutable contract now carries the actual canonical executable CRS definition as deterministic canonical PROJJSON text:

```text
canonical_definition: str
```

`canonical_definition_hash` is a derived property from that canonical definition.

Constructor validation:

1. parses the supplied PROJJSON with the pinned pyproj runtime;
2. re-emits deterministic canonical PROJJSON (`sort_keys=True`, compact separators);
3. normalizes representation/key-order noise to that canonical text;
4. derives and verifies axis name/direction/unit/conversion semantics;
5. derives and verifies `is_geographic` / `is_projected`;
6. if an authority/code is recorded, resolves it under the active pinned runtime and requires exact canonical-definition equality;
7. recomputes `crs_identity_id` from the verified semantic record.

`build_crs_identity()` records an authority/code only when the authority-resolved CRS definition is byte-for-byte identical to the canonical definition. Approximate `to_authority()` matches are not used as attestation. Valid custom/non-authority CRS definitions remain supported because executable semantics are carried by canonical PROJJSON itself.

PROJECT source/target CRS resolution reconstructs directly from the attached canonical definition. AREA re-attests the input CRS at execution and determines projected status and horizontal units from the actual parsed pyproj CRS, not caller-controlled booleans/axis strings.

V1 successful AREA rule:

```text
actual parsed CRS is projected
actual parsed CRS is not geographic
first two horizontal axis units are metre/meter
unit conversion factor == 1.0
```

A geographic CRS therefore cannot produce an `m2` AREA result.

## SPATIAL-H009 — operation execution-engine coherence

`GeometryOperationResult` no longer accepts a detached caller-controlled execution-engine hash. It carries the actual immutable:

```text
engine_identity: GeometryEngineIdentity
```

with `engine_identity_id` exposed only as a derived property.

Successful geometry-producing result invariants:

```text
CANONICALIZE / INTERSECT / PROJECT:
result.engine_identity_id
== output_geometry.engine_identity_id
```

PROJECT additionally preserves:

```text
result.engine_identity_id
== transform_plan.engine_identity_id
== output_geometry.engine_identity_id
```

Official operation functions continue to call `attest_actual_geometry_engine(engine)` before execution. AREA result engine identity means the current operation execution engine; the historical canonicalization engine of the measured input geometry remains committed transitively through the input `semantic_geometry_id` and is not incorrectly required to equal the current AREA runtime.

Operation-result identity continues to commit to the execution engine identity, so an execution-engine semantic/version change changes `operation_id`.

## H008/H009 regressions

Added regressions cover:

- fictional self-consistent projected/metre CRS claims reject;
- EPSG:4326 definition cannot claim projected semantics;
- EPSG:4326 definition cannot claim metre axes;
- authority/code with a different canonical definition rejects;
- detached `canonical_definition_hash` CRS constructor API is removed;
- equivalent PROJJSON key/serialization order normalizes to the same CRS identity;
- canonical CRS definition change changes CRS identity;
- valid non-authority projected CRS remains executable/verifiable;
- real EPSG:4326 AREA cannot produce `m2`;
- real metre-based projected CRS AREA remains valid;
- detached result `engine_identity_id` constructor API is removed;
- successful INTERSECT result engine must match output geometry engine;
- successful PROJECT result engine must match transform-plan engine;
- successful PROJECT result engine must match output geometry engine;
- official INTERSECT result/output engine coherence;
- official PROJECT result/plan/output engine coherence;
- operation execution-engine semantic change changes operation-result identity;
- transform resolution/replay regressions remain green;
- all prior H001–H007 guarantees remain green.

Final spatial baseline after H008/H009:

```text
sitescore-spatial = 136/136 PASS
```

Frozen verification:

```text
sitescore-core      = 86/86 PASS
sitescore-data      = 361/361 PASS
sitescore-providers = 418/418 PASS
```

Authoritative frozen ZIP SHA-256 values remain unchanged:

```text
sitescore-core
aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192

sitescore-data
386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b

sitescore-providers
f45d6843c65025ec60269e3c62f852b8bc23bef731d54af8472288ef4ba72ee2
```

Dependency/import/scope audit remains clean:

```text
SiteScore domain imports from sitescore-spatial = 0
new runtime dependencies = 0
Checkpoint 3.4-2 implementation = 0
CONTRACT_CHANGE_REQUIRED = 0
```

## SPATIAL-H010 — Artifact-engine lineage hardening

Status: RESOLVED.

### CanonicalGeometry historical engine lineage

`CanonicalGeometry` no longer accepts a detached `engine_identity_id` constructor field. It carries the actual immutable, content-bound `GeometryEngineIdentity` object as `engine_identity`; `engine_identity_id` is a derived property only. `semantic_geometry_id` continues to commit to the derived engine identity.

Artifact construction validates the attached engine record's own semantic identity but deliberately does not require it to equal the currently installed runtime. This preserves valid historical/replay artifacts. Current geometry execution through `canonicalize_geometry()` still calls `attest_actual_geometry_engine()` and therefore rejects a historical/fictional engine record as the current runtime.

### TransformPlan engine lineage

`TransformPlan` no longer accepts detached `engine_identity_id`. It carries the actual immutable `GeometryEngineIdentity`; `engine_identity_id` is derived. Plan identity commits to that attached engine object's semantic ID together with source/target CRS, transform policy, exact pipeline hash and grid identities.

`resolve_transform_plan()` attaches the exact engine object that was runtime-attested before transformer selection. Historical plans remain loadable without pretending their engine equals the current runtime; new resolution/execution continues to require active-runtime attestation.

### BoundaryGeometryArtifact engine lineage

`BoundaryGeometryArtifact` no longer stores an independently caller-controlled engine field. Its `engine_identity` and `engine_identity_id` are derived transitively from `canonical_geometry`. The artifact semantic preimage continues to bind that derived engine ID, so there is one authoritative engine-lineage source of truth.

### Operation coherence preserved

For successful CANONICALIZE / INTERSECT / PROJECT results:

- result execution engine semantic ID == output canonical geometry engine semantic ID.
- PROJECT additionally requires transform-plan engine semantic ID == result/output engine semantic ID.

AREA retains the deliberate distinction between the historical input geometry canonicalization engine and the current operation execution engine. They may differ; the current execution engine remains runtime-attested.

### H010 regressions

The suite verifies at minimum:

- detached `CanonicalGeometry.engine_identity_id` construction is impossible;
- self-consistent historical engine lineage is representable as an artifact but rejected for current execution;
- same WKB/CRS/policy with different attached engine semantics changes `semantic_geometry_id`;
- official canonicalization attaches the exact runtime engine object;
- detached `TransformPlan.engine_identity_id` construction is impossible;
- otherwise identical plans with different engine semantics have different `plan_id` values;
- official transform-plan resolution attaches the exact attested engine object;
- boundary artifacts cannot claim engine lineage independently of their canonical geometry;
- official INTERSECT and PROJECT preserve result/output/plan engine coherence;
- AREA may consume a historical canonical geometry produced under a different engine while recording the current execution engine separately.

Final spatial regression baseline after H010: `147/147 PASS`.

Checkpoint 3.4-2 remains unstarted. `CONTRACT_CHANGE_REQUIRED = 0`.

---

## Final artifact-lineage hardening — SPATIAL-H011 / SPATIAL-H012

### SPATIAL-H011 — TransformPlan CRS lineage

`TransformPlan` no longer accepts detached `source_crs_identity_id` / `target_crs_identity_id` constructor fields. The public plan carries the actual immutable, executable CRS sidecars:

```text
source_crs_identity: CRSIdentity
target_crs_identity: CRSIdentity
```

The ID accessors are derived only:

```text
plan.source_crs_identity_id == plan.source_crs_identity.crs_identity_id
plan.target_crs_identity_id == plan.target_crs_identity.crs_identity_id
```

`plan_id` continues to commit to the derived source/target CRS identities together with the actual transform policy, actual engine identity, selected pipeline hash, and canonical grid identities. `resolve_transform_plan()` attaches the exact source and target `CRSIdentity` objects used to construct the single `TransformerGroup` selection. Persistent plan construction validates the attached content-bound CRS objects but does not itself claim that a historical pipeline was freshly selected by the current runtime; current execution/replay retains the existing executable-CRS and strict-pipeline attestation boundaries.

Successful PROJECT result coherence remains structurally enforced by semantic CRS identity:

```text
result.input_crs_identity.crs_identity_id
== plan.source_crs_identity.crs_identity_id

result.output_geometry.crs_identity.crs_identity_id
== plan.target_crs_identity.crs_identity_id
```

### SPATIAL-H012 — GeographyGeometryCompatibility evidence/state lineage

`GeographyGeometryCompatibility` no longer accepts detached geography/artifact/policy identity hashes as public proof. It carries the actual immutable evidence:

```text
geography_identity: GeographyIdentity
geometry_artifact: BoundaryGeometryArtifact
trusted_policy: TrustedGeographyGeometryCompatibilityPolicy
demographic_definition_identity: str
state: CompatibilityState
reason_codes: tuple[str, ...]
```

The convenience IDs are derived transitively from the attached objects. Constructor validation executes the same deterministic compatibility rules used by the official evaluator, derives the expected `COMPATIBLE` or `INCOMPATIBLE` state and exact reason-code set, and rejects any caller-supplied state/reasons that disagree with attached evidence. `compatibility_id` commits to the actual geography, actual artifact, actual trusted policy, actual demographic definition identity, derived state, and derived reasons.

No new matching rule was added. Existing V1 semantics remain:

```text
geography type mismatch                         -> INCOMPATIBLE
canonical geography identifier mismatch         -> INCOMPATIBLE
unexpected trusted geography type                -> INCOMPATIBLE
unexpected demographic definition               -> INCOMPATIBLE
unexpected geometry definition                  -> INCOMPATIBLE
actual geography definition != demographic      -> INCOMPATIBLE
otherwise                                        -> COMPATIBLE
```

`UNRESOLVED` remains reserved for future semantics; this hardening does not invent an unresolved rule merely to exercise the enum.

### Regression baseline after H011/H012

```text
sitescore-spatial = 159/159 PASS
```

New adversarial coverage includes detached source/target CRS constructor rejection, source/target CRS identity sensitivity, exact official resolver object retention, detached compatibility-ID constructor rejection, false COMPATIBLE claims against incompatible definitions/foreign artifacts/trusted-policy mismatch, official compatible/incompatible evaluator paths, and compatibility identity sensitivity to attached evidence/policy semantics.

Frozen dependency baselines reverified from fresh authoritative ZIP extraction:

```text
sitescore-core       = 86/86 PASS
sitescore-data       = 361/361 PASS
sitescore-providers  = 418/418 PASS
```

No SiteScore-domain production imports, new runtime dependencies, benchmark/frame/metric/normalization/readiness implementation, or Checkpoint 3.4-2 scope were introduced.

```text
CONTRACT_CHANGE_REQUIRED = 0
```

---

## Input-evidence hardening — SPATIAL-H013 / SPATIAL-H014

### SPATIAL-H013 — concrete nested semantic-contract types

Public immutable spatial contracts no longer rely on duck-typed attribute compatibility where their semantic identity depends on another hardened spatial contract. Constructor-time checks now require the actual approved contract families before semantic fields are dereferenced or trusted.

At minimum the following are enforced:

```text
GeometrySourceIdentity.source_crs_identity
-> CRSIdentity

GeometryCanonicalizationPolicy.precision_policy
-> GeometryPrecisionPolicy

CanonicalGeometry.crs_identity
-> CRSIdentity
CanonicalGeometry.canonicalization_policy
-> GeometryCanonicalizationPolicy
CanonicalGeometry.engine_identity
-> GeometryEngineIdentity

BoundaryGeometryArtifact.geography_identity
-> GeographyIdentity
BoundaryGeometryArtifact.source_identity
-> GeometrySourceIdentity
BoundaryGeometryArtifact.canonical_geometry
-> CanonicalGeometry
BoundaryGeometryArtifact.canonical_crs_identity
-> CRSIdentity

CRSTransformPolicy.axis_order_policy
-> AxisOrderPolicy

GeometryOperationPolicy.operation
-> GeometryOperation
GeometryOperationPolicy.precision_policy
-> GeometryPrecisionPolicy

GeometryOperationResult.operation
-> GeometryOperation
GeometryOperationResult.state
-> OperationState
GeometryOperationResult.input_geometries[*]
-> CanonicalGeometry
GeometryOperationResult.output_geometry
-> CanonicalGeometry when present
GeometryOperationResult.transform_plan
-> TransformPlan when present
```

The existing `TransformPlan`, compatibility, engine, CRS, policy, and area-policy object checks remain intact. The purpose is contract-lineage integrity, not general Python object sandboxing: a semantic artifact may only rely on an actual immutable spatial contract whose own constructor proves the semantics being consumed.

### SPATIAL-H014 — actual operation input evidence

`GeometryOperationResult` no longer accepts detached caller-controlled:

```text
input_geometry_ids: tuple[str, ...]
input_crs_identity
input_geometry_precision_policy
```

as independent lineage storage.

The public result now carries:

```text
input_geometries: tuple[CanonicalGeometry, ...]
```

and derives:

```text
input_geometry_ids
= tuple(sorted(g.semantic_geometry_id for g in input_geometries))
```

For single-input PROJECT/AREA results, `input_crs_identity` and `input_geometry_precision_policy` remain compatibility/readability properties derived transitively from the actual attached input geometry. They are not constructor-controlled evidence.

Operation identity commits to the derived canonical-sorted input semantic geometry IDs and, for single-input operations, the CRS and precision semantics derived from that exact input artifact.

#### INTERSECT

Successful INTERSECT requires exactly two actual `CanonicalGeometry` inputs. Their CRS semantic identities must match, and the operation precision must match the actual canonicalization precision of each input. The result retains the caller/execution object order as evidence while operation identity uses canonical-sorted semantic IDs, preserving:

```text
A,B vs B,A
-> same operation_id
```

Foreign-CRS input pairs cannot yield a successful result; the official operation preserves both actual inputs in the explicit incompatible result.

#### PROJECT

Successful PROJECT requires exactly one actual source `CanonicalGeometry`. Constructor invariants directly enforce:

```text
input geometry CRS
== transform_plan.source_crs_identity

output geometry CRS
== transform_plan.target_crs_identity

operation precision
== actual input canonicalization precision
```

The official `project_geometry(...)` result retains the exact source `CanonicalGeometry` object used for execution.

#### AREA

Successful AREA requires exactly the measured `CanonicalGeometry`. CRS and input-precision evidence are derived from that artifact rather than separately supplied. The constructor therefore verifies AREA precision, projected/metre CRS semantics, and area-policy/unit coherence against the exact measured geometry.

Historical input canonicalization engine lineage remains attached to the input `CanonicalGeometry`; current AREA execution engine lineage remains the separate runtime-attested result engine. Those engines may legitimately differ.

#### Failure results

Failure results preserve whatever actual canonical input evidence was available at the time of failure. No placeholder or invented input hashes are generated. Empty `input_geometries` remains structurally possible only for failure paths where canonical input evidence genuinely did not exist before failure; official INTERSECT/PROJECT/AREA paths preserve their already-available canonical inputs.

### H013/H014 regressions

New adversarial coverage includes:

- duck-typed fake CRS rejected by `CanonicalGeometry`;
- duck-typed fake canonicalization policy rejected;
- fake source CRS rejected by `GeometrySourceIdentity`;
- fake geography/source/canonical-geometry/CRS objects rejected by `BoundaryGeometryArtifact`;
- fake precision policy rejected by `GeometryCanonicalizationPolicy`;
- enum-like fake operation rejected by `GeometryOperationPolicy`;
- fake output geometry rejected by `GeometryOperationResult`;
- detached `input_geometry_ids` constructor API impossible;
- successful INTERSECT requires exactly two actual inputs;
- official INTERSECT retains actual A/B inputs and remains identity-commutative;
- foreign-CRS INTERSECT cannot become SUCCESS;
- successful PROJECT requires an actual source geometry and verifies plan-source CRS against it;
- official PROJECT retains the exact source geometry object;
- successful AREA requires the exact measured canonical geometry;
- detached AREA input CRS/precision lineage cannot be supplied independently;
- official AREA retains the exact measured geometry;
- changing actual input semantic geometry identity changes operation identity.

Final spatial regression baseline after H013/H014:

```text
sitescore-spatial = 180/180 PASS
```

Frozen baselines reverified from fresh authoritative ZIP extractions:

```text
sitescore-core       = 86/86 PASS
sitescore-data       = 361/361 PASS
sitescore-providers  = 418/418 PASS
```

Authoritative frozen ZIP SHA-256 values remain unchanged. No SiteScore-domain imports, new runtime dependencies, benchmark/frame/metric/normalization/readiness implementation, or Checkpoint 3.4-2 scope was introduced.

```text
CONTRACT_CHANGE_REQUIRED = 0
```
