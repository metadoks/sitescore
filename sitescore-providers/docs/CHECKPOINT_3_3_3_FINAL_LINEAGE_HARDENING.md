# Checkpoint 3.3-3 Final Lineage / Evidence-State Hardening

Scope is limited to FINAL-001 raw->parsed->request->manifest lineage binding and FINAL-002 ACSStatisticalEvidence state/value invariants.

## FINAL-001

Canonical ACS statistical parsing now requires all of the following:

- `response.raw_artifact.request_fingerprint == request.request_fingerprint`
- `response.raw_artifact.provider_identity == _provider_identity(manifest)`
- `response.parsed_artifact.raw_content_hash == response.raw_artifact.content_hash`
- `response.parsed_artifact.parser_id == ACS_PARSER_ID`
- `response.parsed_artifact.parser_version == manifest.parser_version`

`ParsedACSResponse` rejects an unrelated raw/parsed artifact pair at construction time. Provider identity construction remains centralized in the existing canonical `_provider_identity(manifest)` helper; no second ACS identity mapping was introduced.

## FINAL-002

`ACSStatisticalEvidence` constructor enforces semantic axis consistency without re-interpreting Census sentinel strings:

- `VALUE` requires a finite `int|float`, with bool rejected.
- non-`VALUE` requires numeric value `None`.
- `ANNOTATED` requires a non-empty corresponding annotation.
- `VALUE` forbids a non-empty corresponding annotation.
- estimate and MOE axes remain independent.

Official sentinel interpretation remains parser-owned.

No query planner, variable manifest, cross-chunk planning, cohort policy, SourceMetadata, foundation, geocoding/geography, or frozen data contract refactor was performed.
