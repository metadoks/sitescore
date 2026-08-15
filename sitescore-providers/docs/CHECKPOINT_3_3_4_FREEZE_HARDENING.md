# Checkpoint 3.3-4 Freeze Hardening

## FINAL-001 — Partition lineage validation before coverage branching

`build_competition_snapshot()` now validates every supplied `OverturePartitionEvidence`
against the active `OverturePlacesReleaseManifest` before deriving source refs or
branching on `CoverageState`.

The shared pure helper `validate_partitions_against_manifest()` enforces only the
already-established canonical partition requirements:

- `partition.raw_artifact.provider_identity == manifest.provider_identity`
- canonical partition persistence is `PersistenceClass.PERSIST`
- every supplied place binds `release_manifest_identity == manifest.identity`

`OverturePartitionEvidence` remains the owner of raw↔parsed, raw↔SourceMetadata,
and place↔raw/parsed/source-ref internal coherence; those rules are not duplicated.

`deduplicate_places()` reuses the same helper. The snapshot flow is therefore:

1. validate supplied partitions against the active manifest;
2. derive deterministic `source_refs`;
3. branch on coverage state;
4. only for `SUFFICIENT`, deduplicate/classify/count.

Empty partitions remain valid for non-sufficient coverage, preserving the existing
`UNKNOWN`/missing-evidence behavior. Non-empty partitions from another release or
with non-persistent canonical artifacts are rejected under every coverage branch.

No taxonomy, dedup conflict, coverage enum, measurement-definition, catchment,
SourceMetadata, or persistence-policy semantics were changed.
