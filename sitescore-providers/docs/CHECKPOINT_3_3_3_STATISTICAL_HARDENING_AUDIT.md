# Checkpoint 3.3-3 Statistical Evidence / Chunking Hardening Audit

Status: HARDENED — READY FOR LOCK REVIEW

## AUDIT-001 — atomic semantic variable planning

Clean in existing production code. `ACSVariableSpec` is sorted by `semantic_key` and packed as one unit using the width of its complete E/M/optional EA/MA `request_variable_ids`. A spec is never split across the 50-variable boundary. Regression now explicitly verifies atomicity and plan stability under manifest input reordering.

## AUDIT-002 — exact ACS column identity

Hardened. `ACSStatisticalEvidence` is self-contained for originating column identity and now stores exact estimate, MOE, estimate-annotation, and MOE-annotation column IDs plus the originating request fingerprint. Dataset-manifest identity and semantic key remain retained.

## AUDIT-003 — cross-chunk merge coherence

Hardened. Bundle construction validates exact manifest identity, release/vintage, GeographyType/GEOID, originating column mapping, and the deterministic query-plan request fingerprint for each semantic key. Duplicate semantic keys and duplicate originating ACS columns are rejected.

## AUDIT-004 — special value / annotation precedence

Hardened. Official documented numeric sentinels retain their explicit special states. For an otherwise numeric E/M cell, any non-empty EA/MA annotation prevents exposure of the numeric value as ordinary evidence; value becomes `None` with `ANNOTATED` state. Unknown non-empty annotations are never silently treated as `VALUE`.

## AUDIT-005 — determinism statement

Clarified. Same evidence + same manifests/policies + same explicit `generated_at` yields the same frozen `DemographicSnapshot` primitive. Provider `snapshot_identity` intentionally excludes `generated_at` and identifies the derivation, not complete serialized snapshot equality.
