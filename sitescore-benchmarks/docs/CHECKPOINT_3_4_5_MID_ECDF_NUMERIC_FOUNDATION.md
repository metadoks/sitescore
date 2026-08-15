# FAZ 3.4 — CHECKPOINT 3.4-5 MID-ECDF + NUMERIC / NORMALIZATION FOUNDATION

## Status

`READY FOR REVIEW` after implementation, adversarial regression execution, and checkpoint-wide self-audit. This record does **not** declare the checkpoint LOCKED or reviewer-approved.

## Purpose and scope

Checkpoint 3.4-5 establishes the generic deterministic statistical layer immediately after the locked 3.4-4 raw benchmark distribution artifact:

```text
BenchmarkDistributionArtifact
→ canonical finite numeric sample semantics
→ explicit ECDF numeric comparison / tie policy
→ generic mid-ECDF evaluation
→ percentile in [0, 1]
```

This checkpoint does not perform feature-specific normalization or directionality.

Explicitly out of scope:

```text
0–100 feature normalization
competition opportunity inversion
higher-is-better / lower-is-better mapping
feature-specific site/benchmark compatibility orchestration
age fallback integration
COMB-005
ScoringReadiness
RealDataPipelineResult
CategoryScores
Location Score
core.analyze()
```

## Frozen mid-ECDF mathematics

The implemented formula is exactly:

```text
P(d) = (# observations strictly below d + 0.5 × # observations equal to d) / N
```

where `N` is the full multiplicity-preserving canonical numeric sample size.

No alternative percentile convention is used.

No interpolation is used.

No endpoint override is used.

Consequences are therefore formula-derived:

```text
d < min(sample)  -> P(d) = 0
d > max(sample)  -> P(d) = 1
```

For an observed endpoint, the half-tie term remains active. For example, with one unique observed minimum among `N` observations:

```text
P(min) = 0.5 / N
```

and with one unique observed maximum:

```text
P(max) = (N - 1 + 0.5) / N
```

All observations tied at the query produce `P(d) = 0.5` for any non-empty `N`.

## Public contracts

### NumericComparisonPolicy

`NumericComparisonPolicy` is a separate versioned ECDF numeric/tie contract.

Canonical V1:

```text
EXACT_NUMERIC_COMPARISON_V1
policy_id = ecdf_numeric_comparison
policy_version = 1.0
equality_rule = EXACT_CANONICAL_NUMERIC_VALUE
ordering_rule = EXACT_CANONICAL_NUMERIC_ORDER
tolerance_rule = NO_TOLERANCE_NO_ROUNDING_NO_QUANTIZATION
```

Only canonical V1 comparison semantics are accepted by canonical sample/evaluation objects in this checkpoint.

No epsilon, decimal scale, relative tolerance, absolute tolerance, ULP threshold, or rounding precision is introduced.

### MidEcdfPolicy

Canonical V1:

```text
MID_ECDF_V1
policy_id = mid_ecdf
policy_version = 1.0
formula_rule = BELOW_PLUS_HALF_EQUAL_DIVIDED_BY_N
interpolation_rule = STEP_FUNCTION_NO_INTERPOLATION
```

The policy binds the actual `NumericComparisonPolicy` object through its semantic identity.

### CanonicalNumericSample

`CanonicalNumericSample` is the deliberately pure numeric helper.

It accepts only a tuple of legitimate finite Python real numerics:

```text
finite int   -> accepted
finite float -> accepted
bool         -> rejected
NaN          -> rejected
+Inf / -Inf  -> rejected
None         -> rejected
other types  -> rejected
```

It does not silently coerce or drop invalid values.

Its semantic identity is order-insensitive but multiplicity-sensitive.

Examples:

```text
[1, 2, 2, 3] and [3, 2, 1, 2] -> same sample identity
[1, 1, 2] and [1, 2]           -> different sample identity
```

This pure helper intentionally carries no benchmark-domain lineage. It must not be mistaken for evidence that a benchmark distribution exists.

### BenchmarkNumericSample

`BenchmarkNumericSample` is the domain-bound adapter from an actual `BenchmarkDistributionArtifact`.

It accepts only an actual distribution with:

```text
BenchmarkDistributionState.AVAILABLE
```

Therefore these states are rejected before ECDF evaluation:

```text
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

It consumes exactly the authoritative 3.4-4 `BenchmarkObservation` population. It does not reconstruct values from excluded attempts.

Its semantic identity binds:

```text
distribution_id
comparison policy identity
pure canonical numeric sample identity
actual observation IDs
```

Thus unrelated benchmark distributions with coincidentally equal numeric values do not collapse into the same domain artifact identity.

### MidEcdfState

Generic evaluation states:

```text
AVAILABLE
EMPTY_SAMPLE
```

An empty pure numeric sample produces `EMPTY_SAMPLE` and `percentile = None`. It never fabricates 0, 0.5, or 1.

### MidEcdfEvaluation

The constructor accepts only:

```text
sample
query
policy
```

The following are derived and cannot be caller asserted:

```text
N
below_count
equal_count
percentile
state
reason_codes
evaluation identity
```

The available percentile is guaranteed to satisfy:

```text
0.0 <= percentile <= 1.0
```

### BenchmarkMidEcdfEvaluation

This domain-bound result wraps an actual `BenchmarkNumericSample` and a generic `MidEcdfEvaluation`.

Its identity binds both:

```text
benchmark sample / distribution lineage
numeric ECDF evaluation identity
```

This separates pure numeric mathematics from benchmark-domain provenance without detached caller-supplied lineage IDs.

## Canonical numeric equality and representation

Python representation details are not semantic when the represented numeric value is exactly equal under V1 rules.

Internally, accepted numeric values are canonicalized to exact reduced rational pairs for comparison/identity purposes:

```text
(numerator, denominator)
```

Finite floats use their exact `as_integer_ratio()` value; integers use denominator `1`. Zero is canonicalized to `(0, 1)`.

Therefore:

```text
1 and 1.0     -> equal/tied and identity-equivalent
-0.0 and 0.0  -> equal/tied and identity-equivalent
```

Very close but non-equal finite values remain distinct. No epsilon merges them.

This rational canonicalization is an ECDF comparison/identity technique; it does not change the upstream measurement representation contract.

## Precision-policy separation

Three distinct concepts remain separate:

### GeometryPrecisionPolicy

Owned by `sitescore-spatial` and controls geometry precision/canonicalization semantics.

### MeasurementPrecisionPolicy

Owned by `sitescore-metrics`. V1 measurement representation remains `FULL_BINARY64`.

### NumericComparisonPolicy

Owned here for ECDF equality/order/tie semantics. V1 is exact numeric equality with no tolerance.

These policies are not aliases and their identities are not interchangeable.

`FULL_BINARY64.identity_id` is not reused as an ECDF tie-policy identity.

## Multiplicity and ordering

Input order is non-semantic.

Multiplicity is semantic.

Equal observations are not deduplicated because mid-ECDF requires exact tie counts.

Canonical sample identity sorts canonical numeric values while retaining every occurrence.

No `set` conversion is used for the observation population.

## Empty and incompatible benchmark artifacts

A 3.4-4 artifact without a usable comparable numeric observation population cannot produce an available domain ECDF result.

Specifically:

```text
NO_NUMERIC_OBSERVATIONS          -> benchmark numeric sample construction rejected
EMPTY_ELIGIBLE_POPULATION        -> benchmark numeric sample construction rejected
INCOMPATIBLE_MEASUREMENT_LINEAGE -> benchmark numeric sample construction rejected
```

This preserves:

```text
no numeric observations != percentile 0
no numeric observations != percentile 0.5
no numeric observations != percentile 1
```

## Structural evaluability vs empirical adequacy

Checkpoint 3.4-5 implements mathematical evaluability only.

No empirical benchmark adequacy policy is invented.

Still unresolved:

```text
minimum benchmark N
minimum coverage ratio
minimum unique-value count
variance requirement
production sample adequacy threshold
```

Any non-empty structurally valid numeric sample is mathematically evaluable by the frozen mid-ECDF formula. That is not a claim that the sample is empirically adequate for production scoring.

## Dependency DAG

No dependency metadata changed in checkpoint 3.4-5.

`sitescore-benchmarks` runtime dependencies remain:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

No new third-party runtime dependency was introduced. `fractions.Fraction` is Python standard library only.

Forbidden dependencies remain absent:

```text
sitescore-benchmarks -> sitescore-core       = 0
sitescore-benchmarks -> sitescore-pipeline   = 0
sitescore-benchmarks -> sitescore-data       = 0 direct import
sitescore-benchmarks -> sitescore-providers  = 0 direct import
```

The approved existing path through `sitescore-metrics` remains unchanged.

## Identity semantics

### Pure sample identity binds

```text
comparison-policy identity
canonical sorted numeric values
full multiplicity
N
```

It does not bind input order, timestamps, paths, or worker order.

### Benchmark sample identity binds

```text
actual BenchmarkDistributionArtifact.distribution_id
comparison-policy identity
pure sample identity
actual observation IDs
```

### Generic ECDF evaluation identity binds

```text
sample identity
mid-ECDF policy identity
comparison-policy identity
canonical query numeric value
state/reason
N
below_count
equal_count
percentile
```

### Domain ECDF result identity additionally binds

```text
benchmark sample identity
underlying distribution identity
numeric evaluation identity
```

No caller supplies counts, percentile, or detached benchmark lineage IDs.

## Failure semantics

Programming/type contract failures raise deterministic `TypeError` or `ValueError`.

Examples:

```text
bool numeric input                  -> TypeError
None/unsupported numeric type       -> TypeError
NaN/Inf                             -> ValueError
unsupported comparison policy       -> ValueError
unsupported mid-ECDF policy         -> ValueError
non-AVAILABLE benchmark distribution -> ValueError
```

A pure empty sample is not a programming failure; it yields typed `EMPTY_SAMPLE` with `percentile=None`.

No catch-all fallback produces zero or a neutral percentile.

## Regression matrix

Implemented adversarial/mathematical coverage includes:

```text
ECDF-001 basic unique sample
ECDF-002 tied middle value
ECDF-003 all equal -> 0.5
ECDF-004 below minimum -> 0
ECDF-005 above maximum -> 1
ECDF-006 observed minimum midpoint semantics
ECDF-007 observed maximum midpoint semantics
ECDF-008 no interpolation
ECDF-009 multiplicity preserved
ECDF-010 permutation determinism
ECDF-011 close-but-unequal values remain distinct
ECDF-012 1/1.0 and -0.0/0.0 representation equivalence
ECDF-013 bool rejected
ECDF-014 NaN/Inf/None rejected
ECDF-015 empty sample explicit
ECDF-016 no-observation 3.4-4 artifact rejected
ECDF-017 incompatible 3.4-4 artifact rejected
ECDF-018 percentile bounds
ECDF-019 counts/percentile derived only
ECDF-020 no feature-score/later-checkpoint leakage
```

Additional regressions cover policy separation, unsupported policy rejection, benchmark-domain lineage preservation, representation-stable query identity, and multiplicity after canonical ordering.

## Test evidence

Initial validation exposed only three test-fixture registration errors; production source had no failing assertion. The local `frame3` fixture was then registered in the new ECDF test module.

Successful validation run:

```text
workflow: cp345-validation
run id: 31896419345
validated commit: 932b86d8f740b33a063daedbeb5527798c54dfdc
```

Visible suite result:

```text
sitescore-benchmarks: 142/142 PASS
```

The same GitHub Actions job also completed the locked `sitescore-metrics`, `sitescore-spatial`, `sitescore-providers`, `sitescore-data`, and `sitescore-core` package test steps successfully.

A final documentation-inclusive validation is required before reviewer handoff and will supersede this intermediate evidence.

## Scope audit

Not implemented:

```text
feature-specific normalized values
0–100 conversion
competition inversion
feature directionality
site/benchmark feature compatibility orchestration
age fallback
COMB-005
road_parking_access_score
ScoringReadiness
RealDataPipelineResult
CategoryScores
Location Score
core.analyze()
```

No checkpoint 3.4-6 work is included.

## CONTRACT_CHANGE_REQUIRED

```text
0
```

The locked 3.4-4 contracts at main SHA `989b719d84a4fa01d40c0a2d342cdeff9197c3e7` were sufficient as additive input. No frozen upstream semantic contract required modification.
