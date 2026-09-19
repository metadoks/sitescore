# FAZ 3.3 — Checkpoint 3.3-1 Provider Foundation

## Scope

Implemented only provider-independent acquisition foundations:

- immutable provider identity
- deterministic request fingerprints
- canonical provider-layer JSON/hash primitives
- exact raw-content identity and artifact references
- parsed-artifact lineage
- generic persistence decisions and provider policy registry protocol
- typed provider execution errors and acquisition results
- backend-neutral artifact-store protocol
- canonical `SourceMetadata` builder into frozen `sitescore-data v0.1.0`
- runtime version guard plus repository frozen-baseline preflight record

## Frozen boundary

`sitescore-providers -> sitescore-data==0.1.0`

No `sitescore-core` dependency/import is permitted.

Authoritative `sitescore-data` freeze identity:

- commit `f03cbb71bd93c5a3afd78b43991e456595a7f75d`
- tag `sitescore-data-v0.1.0`
- tests `361/361 PASS`

Git identity is deliberately not a runtime import requirement.

## Identity rules

Raw artifact canonical identity is the exact content hash. `retrieved_at` is provenance and is excluded from identity.

Parsed identity commits to:

- raw content hash
- parser id
- parser version
- provider-layer canonical primitive representation of parsed output

Request fingerprint commits only to semantic request inputs and policy/source identity. Execution metadata, credentials, retry counters, timestamps, local paths, and request IDs are not accepted as fingerprint inputs.

## Persistence policy

Foundation models only generic persistence semantics. It contains no provider-specific legal or retention tables.

## Evidence-state boundary

Provider execution failures are not `AvailabilityState` values. Domain builders introduced in later checkpoints own any mapping from acquisition outcomes to frozen domain evidence states.

## Structured provider-internal artifacts

Future structured artifacts such as ACS statistical evidence can be converted to provider-layer canonical bytes, content-hashed, and stored behind `ArtifactStore` without adding ACS-specific fields to this foundation.

## Explicitly deferred

No Census/geocoder/ACS/Overture/OSM/Valhalla/GTFS/parking provider, no HTTP client, no storage backend, no benchmark builder, no normalization, no app integration, and no core adapter are implemented here.

## Hardening disposition

### Parsed content vs derivation identity

`ParsedArtifact.parsed_content_hash` is the SHA-256 of the canonical parsed primitive only. It is content identity, independent of raw lineage and parser version.

`ParsedArtifact.derivation_fingerprint` is the lineage-aware artifact identity and commits to:

- raw content hash,
- parser ID,
- parser version,
- canonicalization version,
- parsed content hash.

`ParsedArtifact.identity` returns `derivation_fingerprint`.

### Canonicalization grammar

Provider canonicalization is explicitly identified by `CANONICALIZATION_VERSION = "v1"`. Any semantics-changing change to canonical primitive conversion or canonical JSON encoding requires a canonicalization-version bump. This is provider-layer semantics and does not modify `sitescore-data.serialization`.

### SOURCE_POLICY retention semantics

`SOURCE_POLICY` means retention is not concretely resolved by this `PersistenceDecision`; therefore `expires_at` and `max_retention_seconds` must both be `None`. When a source policy is actually resolved, the policy registry should return a new concrete `PersistenceDecision` using `PERSIST`, `TRANSIENT`, or `DO_NOT_PERSIST`. A `TRANSIENT` concrete decision carries exactly one temporal rule: either absolute `expires_at` or relative `max_retention_seconds`, never both.
