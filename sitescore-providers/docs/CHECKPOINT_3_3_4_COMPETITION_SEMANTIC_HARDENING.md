# Checkpoint 3.3-4 Competition Semantic Hardening

Scope: FIX-001 through FIX-004 and DOC-001 only. Checkpoint 3.3-5 is not implemented.

## FIX-001 Taxonomy resolution

Canonical V1 resolution is versioned by `TaxonomyResolutionPolicy` and fixed to hierarchy -> primary -> basic_category fallback/QA. Alternate taxonomy categories are supporting-only and cannot independently qualify, exclude, promote, or veto a place. The taxonomy mapping identity commits to the resolution-policy identity.

## FIX-002 Exact-ID deduplication

Exact Overture Place ID duplicates collapse only when canonical measurement-relevant evidence matches: coordinates, basic category, taxonomy primary/hierarchy/alternates, operating status, confidence, source attributions, and release identity. Conflicts reject rather than using first-record-wins. Different attribution evidence is treated as a conflict in V1; no attribution is silently discarded.

## FIX-003 Taxonomy parsing

Taxonomy hierarchy and alternates are type-checked before tuple/sort canonicalization. A present taxonomy requires non-empty primary/hierarchy, `primary == hierarchy[-1]`, unique hierarchy/alternate values, and alternates outside the primary hierarchy.

## FIX-004 Policy identity grammar

`PlaceLifecyclePolicy.identity` and `EntityDedupPolicy.identity` now explicitly commit to their provider-layer grammar versions and `CANONICALIZATION_VERSION`.

## DOC-001 Release record

Official Overture release documentation checked on 2026-08-12 identifies data release `2026-07-22.0` and schema `v1.18.0`. Production code does not encode this as a mutable latest/current selection; exact release configuration remains deployment-supplied.
