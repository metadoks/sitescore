# SiteScore AI — Implementer → Reviewer Handoff

HANDOFF_PROTOCOL_VERSION: 1.0
AUTHORITATIVE_REPO: metadoks/sitescore
COORDINATION_BRANCH: ops/reviewer-implementer-handoff
FILE_OWNER: IMPLEMENTER CHAT

CURRENT_PHASE: FAZ 3.4
CURRENT_CHECKPOINT: 3.4-5
IMPLEMENTER_STATE: READY_FOR_REVIEW

CHECKPOINT: FAZ 3.4-5
CHECKPOINT_TITLE: Mid-ECDF + Numeric / Normalization Foundation
BASE_SHA: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
CODE_BRANCH: faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
CODE_HEAD_SHA: 4e2d44178141e2715b18283917288bfc829dd42e
PR: #2
CONTRACT_CHANGE_REQUIRED: 0

---

## 1. Executive implementation summary

Implemented the generic deterministic statistical foundation immediately after locked checkpoint 3.4-4:

```text
BenchmarkDistributionArtifact
→ canonical finite numeric sample
→ explicit exact numeric comparison/tie policy
→ generic mid-ECDF evaluation
→ percentile in [0, 1]
```

The frozen formula is implemented directly:

```text
P(d) = (# observations strictly below d + 0.5 × # observations equal to d) / N
```

No interpolation, endpoint override, feature-specific directionality, 0–100 conversion, competition inversion, empirical adequacy threshold, readiness, or core scoring was introduced.

## 2. Git state

```text
repository: metadoks/sitescore
base branch: main
base SHA: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
code branch: faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
code HEAD: 4e2d44178141e2715b18283917288bfc829dd42e
PR: #2
PR base: main
PR head: faz3.4/cp3.4-5-mid-ecdf-numeric-foundation
PR state: OPEN
```

The branch was created from the exact reviewer-specified merged 3.4-4 main SHA. No duplicate branch existed when creation was performed.

## 3. Changed files

Final base-to-HEAD diff contains six files, all under `sitescore-benchmarks`:

```text
sitescore-benchmarks/README.md
sitescore-benchmarks/docs/CHECKPOINT_3_4_5_MID_ECDF_NUMERIC_FOUNDATION.md
sitescore-benchmarks/src/sitescore_benchmarks/__init__.py
sitescore-benchmarks/src/sitescore_benchmarks/ecdf.py
sitescore-benchmarks/tests/test_architecture.py
sitescore-benchmarks/tests/test_mid_ecdf.py
```

Purpose:

- `ecdf.py`: new canonical numeric/tie/mid-ECDF contracts and builders/evaluators.
- `__init__.py`: exports the new public 3.4-5 surface.
- `test_mid_ecdf.py`: mathematical and adversarial regression matrix.
- `test_architecture.py`: advances architecture guard from “no ECDF” to “ECDF allowed, later normalization/scoring still forbidden”, and explicitly guards against hidden epsilon/tolerance constants.
- checkpoint doc: authoritative implementation record, precision separation, identities, failure semantics, unresolved adequacy decisions, test evidence, scope audit.
- README: package scope updated through 3.4-5.

No `pyproject.toml`, lockfile, upstream package, or dependency declaration changed.

## 4. Public contracts added or changed

Added:

```text
NumericComparisonPolicy
EXACT_NUMERIC_COMPARISON_V1
MidEcdfPolicy
MID_ECDF_V1
CanonicalNumericSample
BenchmarkNumericSample
MidEcdfState
MidEcdfEvaluation
BenchmarkMidEcdfEvaluation
build_numeric_sampleuild_benchmark_numeric_sample
evaluate_mid_ecdf
evaluate_benchmark_mid_ecdf
```

These are exported from `sitescore_benchmarks`.

No locked 3.4-4 contract was modified.

## 5. Exact implemented behavior

### Mid-ECDF

For a non-empty canonical sample:

```text
below_count = count(value < query)
equal_count = count(value == query)
N = full sample multiplicity
P = (below_count + 0.5 * equal_count) / N
```

Operational implementation uses the algebraically equivalent exact count expression:

```text
(2 * below_count + equal_count) / (2 * N)
```

Required behavior is preserved:

```text
[1,2,3], query=2             -> 0.5
[1,2,2,2,3], query=2         -> 0.5
all values tied to query     -> 0.5
query below minimum          -> 0.0
query above maximum          -> 1.0
[1,2,3], query=min=1         -> 1/6
[1,2,3], query=max=3         -> 5/6
[1,3], query=2               -> 0.5 with no interpolation
```

Counts, N, percentile, state and result identity are derived from the actual canonical sample; there is no caller-supplied count or percentile path.

## 6. Numeric / tie semantics

V1 ECDF equality/order is explicitly separate from geometry and measurement precision.

Canonical policy:

```text
EXACT_NUMERIC_COMPARISON_V1
EXACT_CANONICAL_NUMERIC_VALUE
EXACT_CANONICAL_NUMERIC_ORDER
NO_TOLERANCE_NO_ROUNDING_NO_QUANTIZATION
```

Accepted numeric domain:

```text
finite int   -> accepted
finite float -> accepted
bool         -> rejected
None         -> rejected
NaN          -> rejected
+Inf / -Inf  -> rejected
```

Accepted values are canonicalized to exact reduced rational pairs for comparison and identity. Finite floats use their exact `as_integer_ratio()` representation; integers use denominator 1; both signed zero forms become `(0, 1)`.

Therefore:

```text
1 == 1.0 for V1 tie/identity semantics
-0.0 == 0.0 for V1 tie/identity semantics
```

Very close but unequal values, including `math.nextafter(1.0, 2.0)`, remain distinct. No epsilon is applied.

Multiplicity is retained; no set/dedup conversion exists.

## 7. Empty / unavailable semantics

Pure `CanonicalNumericSample(())` is structurally representable. Evaluation returns:

```text
state = EMPTY_SAMPLE
reason_codes = ("empty_numeric_sample",)
percentile = None
```

It does not fabricate 0, 0.5 or 1.

Domain-bound `BenchmarkNumericSample` requires actual 3.4-4 state `AVAILABLE` and actual observations. Therefore these are rejected before domain ECDF evaluation:

```text
EMPTY_ELIGIBLE_POPULATION
NO_NUMERIC_OBSERVATIONS
INCOMPATIBLE_MEASUREMENT_LINEAGE
```

Excluded 3.4-4 attempts are never reconstructed as numeric values.

## 8. Identity / lineage design

`CanonicalNumericSample` is deliberately a pure numeric helper. Its identity binds:

```text
comparison-policy identity
canonical sorted numeric values
full multiplicity
N
```

Input order is non-semantic; multiplicity is semantic.

`BenchmarkNumericSample` additionally binds actual domain lineage:

```text
BenchmarkDistributionArtifact.distribution_id
comparison-policy identity
pure numeric sample identity
actual observation IDs
```

Thus unrelated distributions with coincidentally identical numeric values do not collapse to the same domain sample identity.

Generic `MidEcdfEvaluation` identity binds:

```text
sample identity
mid-ECDF policy identity
comparison-policy identity
canonical query numeric value
state/reasons
N
below_count
equal_count
percentile
```

`BenchmarkMidEcdfEvaluation` additionally binds benchmark sample/distribution lineage.

No detached caller-supplied distribution ID, counts or percentile is trusted.

## 9. Dependency changes

Dependency metadata changes:

```text
none
```

Existing `sitescore-benchmarks` runtime dependencies remain:

```text
sitescore-spatial==0.1.0
sitescore-metrics==0.1.0
```

New third-party runtime dependency:

```text
none
```

`fractions.Fraction` is Python standard library.

## 10. Tests

Final documentation-inclusive GitHub Actions validation:

```text
workflow: cp345-validation
run id: 31896517539
validated commit: cc32f3abdb080ecee97f812b65b1c7a076645e42
conclusion: SUCCESS
```

Executed package-root suites:

```text
sitescore-benchmarks: 142/142 PASS
sitescore-metrics:     67/67 PASS
sitescore-spatial:     PASS
sitescore-providers:   PASS
sitescore-data:        PASS
sitescore-core:        PASS
```

The locked frozen package suite steps all completed successfully in the same job. Their established suite sizes remain spatial 180, providers 418, data 361 and core 86; no source in those packages changed in this checkpoint.

The final code HEAD is:

```text
4e2d44178141e2715b18283917288bfc829dd42e
```

GitHub comparison verifies that the only delta from validated commit `cc32f3ab...` to final HEAD is removal of the temporary branch-only workflow:

```text
.github/workflows/cp345-validation.yml
```

Source, tests and documentation are unchanged between validated commit and review HEAD.

An earlier validation run had `139 passed, 3 errors`; all three errors were test fixture registration (`frame3` was not registered in the new module), not production assertion failures. The fixture was registered locally and subsequent full validations passed.

## 11. Adversarial regressions

Coverage includes all reviewer-required ECDF cases:

```text
ECDF-001 basic unique sample
ECDF-002 tied middle
ECDF-003 all equal
ECDF-004 below minimum
ECDF-005 above maximum
ECDF-006 observed minimum midpoint
ECDF-007 observed maximum midpoint
ECDF-008 no interpolation
ECDF-009 duplicate multiplicity preserved
ECDF-010 permutation determinism
ECDF-011 exact equality/no epsilon
ECDF-012 1 vs 1.0 and -0.0 vs 0.0
ECDF-013 bool rejected
ECDF-014 NaN/Inf/None rejected
ECDF-015 empty sample no fabricated percentile
ECDF-016 no-observation 3.4-4 artifact rejected
ECDF-017 incompatible 3.4-4 artifact rejected
ECDF-018 output bounds
ECDF-019 counts/percentile derived
ECDF-020 no feature-score leakage
```

Additional regressions cover unsupported policy rejection, separation from `FULL_BINARY64`, domain lineage preservation for coincident numeric values, query representation-stable identity, and multiplicity after canonical ordering.

## 12. Dependency / DAG audit

```text
benchmarks -> core imports:       0
benchmarks -> pipeline imports:   0
benchmarks -> data direct imports: 0
benchmarks -> providers direct imports: 0
metrics -> benchmarks imports:    0 (locked baseline preserved)
new dependency cycles:            0 observed
```

Approved `benchmarks -> spatial` and `benchmarks -> metrics` edges remain unchanged.

## 13. Scope audit

Not implemented:

```text
0–100 feature normalization
feature-specific directionality
competition opportunity inversion
feature-specific site/benchmark compatibility orchestration
age fallback integration
COMB-005
road_parking_access_score
ScoringReadiness
RealDataPipelineResult
CategoryScores
Location Score
core.analyze()
```

No checkpoint 3.4-6 implementation was started.

## 14. Documentation updates

Added:

```text
sitescore-benchmarks/docs/CHECKPOINT_3_4_5_MID_ECDF_NUMERIC_FOUNDATION.md
```

Updated:

```text
sitescore-benchmarks/README.md
```

The checkpoint document records formula, policy separation, numeric domain, representation equivalence, identity/lineage, empty/unavailable behavior, DAG, tests, scope and unresolved decisions.

## 15. Known unresolved / calibration-gated decisions preserved

No empirical adequacy rule was invented. These remain unresolved for later approved policy/calibration work:

```text
minimum benchmark N
minimum benchmark coverage ratio
minimum unique-value count
variance requirement
production benchmark adequacy threshold
```

Existing upstream unresolved decisions such as production equal-area configuration, metric-specific unresolved reductions and COMB-005 also remain untouched.

Structural ECDF evaluability is explicitly not treated as empirical adequacy.

## 16. Self-audit result

```text
frozen mid-ECDF formula                     VERIFIED
no interpolation                            VERIFIED
endpoint behavior formula-derived           VERIFIED
all-tied -> 0.5                             VERIFIED
exact/no-tolerance tie semantics             VERIFIED
1 / 1.0 canonical equivalence               VERIFIED
-0.0 / 0.0 canonical equivalence            VERIFIED
close unequal values remain distinct         VERIFIED
multiplicity retained                        VERIFIED
input order non-semantic                     VERIFIED
invalid numeric inputs rejected              VERIFIED
empty sample does not fabricate percentile   VERIFIED
3.4-4 unavailable/incompatible gating        VERIFIED
benchmark distribution lineage retained      VERIFIED
caller-supplied counts/percentile path        NONE
feature-score/directionality leakage          NONE OBSERVED
hidden empirical threshold                   NONE
new dependency                               NONE
frozen upstream source mutation              NONE
CONTRACT_CHANGE_REQUIRED                     0
```

## 17. Reviewer attention points

Please focus independent review on:

1. exact rational canonicalization used to make `1`/`1.0` and signed zero representation-equivalent without epsilon;
2. `NumericComparisonPolicy` remaining semantically separate from `MeasurementPrecisionPolicy/FULL_BINARY64`;
3. multiplicity preservation and order-insensitive canonical sample identity;
4. distinction between pure `CanonicalNumericSample` and domain-bound `BenchmarkNumericSample`;
5. requirement that domain ECDF evaluation consumes only `AVAILABLE` 3.4-4 distributions;
6. result identity deriving N/below/equal/percentile rather than trusting caller fields;
7. absence of feature normalization, directionality and competition inversion;
8. validated commit `cc32f3ab...` to final review HEAD `4e2d4417...` being workflow-removal-only.

## 18. Final implementer state

```text
IMPLEMENTER_STATE: READY_FOR_REVIEW
CHECKPOINT: FAZ 3.4-5
BASE_SHA: 989b719d84a4fa01d40c0a2d342cdeff9197c3e7
CODE_HEAD_SHA: 4e2d44178141e2715b18283917288bfc829dd42e
PR: #2
CONTRACT_CHANGE_REQUIRED: 0
```

No merge, user-controlled LOCK transition, tag, or checkpoint 3.4-6 work was performed.
