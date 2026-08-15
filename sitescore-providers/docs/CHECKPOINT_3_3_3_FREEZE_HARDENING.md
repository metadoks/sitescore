# Checkpoint 3.3-3 Freeze Hardening

Scope: FINAL-003 direct ACSEvidenceBundle validation bypass and FINAL-004 SourceMetadata semantic provenance binding only.

## FINAL-003

`build_demographic_snapshot()` reuses `build_evidence_bundle()` as the single canonical validation path before demographic construction. Direct `ACSEvidenceBundle` construction therefore cannot bypass deterministic request-fingerprint, exact E/M/EA/MA column, manifest, release/vintage, geography, or duplicate-origin validation.

## FINAL-004

ACS SourceMetadata is validated against the active manifest through the canonical `_provider_identity(manifest)` mapping before raw content hashes are used for evidence-to-source lookup. Required semantic equality covers provider, dataset, dataset release, vintage, and schema version. Exact raw content hash matching remains independently required.

No SourceMetadata schema change was made.

## Verification

- provider tests: 205/205 PASS
- sitescore-data frozen tests: 361/361 PASS
- sitescore-core frozen tests: 86/86 PASS
- runtime dependency: sitescore-data==0.1.0 only
- sitescore-core imports: 0
- CONTRACT_CHANGE_REQUIRED: 0

Checkpoint 3.3-4 was not started.
