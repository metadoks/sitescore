# FAZ 3.3 Provider Freeze Record

## Freeze status

- FAZ 3.3 status: **FROZEN**
- Package: `sitescore-providers`
- Version: `0.1.0`
- Freeze decision: first repository-level provider freeze; no version bump beyond `0.1.0`.
- `CONTRACT_CHANGE_REQUIRED = 0`

## Locked checkpoints

- Checkpoint 3.3-1 Foundation — LOCKED
- Checkpoint 3.3-2 Geography — LOCKED
- Checkpoint 3.3-3 ACS — LOCKED
- Checkpoint 3.3-4 Competition — LOCKED
- Checkpoint 3.3-5 Pedestrian — LOCKED
- Checkpoint 3.3-6 Transit — LOCKED
- Checkpoint 3.3-7 Road — LOCKED
- Checkpoint 3.3-8 Parking — LOCKED

## Authoritative freeze input

Freeze input was exactly `sitescore-providers-checkpoint-3.3-8-hardened.zip`.

- SHA-256: `41e3fa4f7b65beca334d75046c89b179309c963c783dad7576dd72a4490e5c74`

All eight final checkpoint ZIP hashes were independently rechecked before freeze and matched their locked records. Byte-level production-file comparison from each locked checkpoint to the cumulative 3.3-8 tree reported `changed=0` and `missing=0` for every production file that existed at that checkpoint.

## Package / dependency boundary

`pyproject.toml`:

- package version: `0.1.0`
- runtime dependencies: exactly `sitescore-data==0.1.0`
- `sitescore-core` production imports: `0`
- new third-party runtime dependencies: `0`

Explicitly absent as runtime dependencies: `requests`, `httpx`, `aiohttp`, `pandas`, `geopandas`, `shapely`, `pyproj`, `duckdb`, GTFS libraries, and Valhalla Python bindings.

## Final production tree

```text
src/sitescore_providers/
├── __init__.py
├── _validation.py
├── artifacts.py
├── baseline.py
├── errors.py
├── hashing.py
├── http.py
├── identity.py
├── lineage.py
├── parsing.py
├── policy.py
├── results.py
├── acs/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   ├── parser.py
│   └── request.py
├── census/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   ├── parser.py
│   └── policy.py
├── overture/
│   ├── __init__.py
│   ├── builders.py
│   ├── models.py
│   ├── parser.py
│   └── reader.py
├── pedestrian/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   └── parser.py
├── transit/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   └── parser.py
├── road/
│   ├── __init__.py
│   ├── builders.py
│   ├── client.py
│   ├── models.py
│   └── parser.py
└── parking/
    ├── __init__.py
    ├── builders.py
    ├── models.py
    ├── parser.py
    └── reader.py
```

Scope audit found no production implementation for benchmark ECDF, normalization, `road_parking_access_score`, `RealDataPipelineResult` orchestration, app integration, or a core adapter.

## Cross-cutting frozen invariants

The final source-level audit preserves these FAZ 3.3 invariants:

- missing evidence is not zero;
- unknown is not false;
- out-of-validity is not zero;
- provider failure is not negative site evidence;
- no silent fallback or provider substitution;
- no mutable `latest` / `current` / `live` canonical identities;
- semantic identity is distinct from storage/download locators;
- `ArtifactRef`, URL, endpoint, cache/storage path, worker/retry metadata and retrieval timestamps do not enter semantic hashes unless a field is intrinsically semantic;
- request fingerprints represent semantic provider requests, not execution noise;
- raw bytes/content hash, parsed artifact identity and `SourceMetadata` remain provenance-coherent;
- processing/caller input order cannot alter semantic identity where order is not semantic;
- source observation timestamps remain semantic where the evidence contract requires them, while unrelated `retrieved_at` remains non-semantic;
- provider-specific rich lineage may remain provider-side instead of leaking into frozen `sitescore-data`;
- provider-side scoring/calibration is absent from FAZ 3.3.

## Frozen dependency verification

### sitescore-data v0.1.0

- ZIP SHA-256: `386b9b919d9aafccca5ac80e55fb15864cb5f74dd5408abcc86af58b2b3ae80b`
- commit: `f03cbb71bd93c5a3afd78b43991e456595a7f75d`
- tag: `sitescore-data-v0.1.0`
- tests: `361/361 PASS`

### sitescore-core v0.1.0

- ZIP SHA-256: `aeb6c82b2f698a2d01f5964fff9f274741176feb785a942e0e81222279d3f192`
- commit: `019b40beadb66c533f1de41e99efc7084663956f`
- tag: `v0.1.0`
- tests: `86/86 PASS`

Providers were tested against frozen `sitescore-data` directly; no provider-to-core dependency was introduced for verification.

## Provider test baseline

- Pre-freeze authoritative source: `418/418 PASS`
- Final freeze tree: `418/418 PASS`

## Authoritative handoff records

These records are preserved byte-for-byte:

- `docs/FAZ3_3_PROVIDER_HANDOFF.md`
  - SHA-256: `fe9df4ac5cc02273bc86f5b5e529f7335dd52b48db6030e0d2d5bda9d6892a15`
- `docs/FAZ3_4_NEW_CHAT_BOOTSTRAP.md`
  - SHA-256: `5e0b83372c9b23dc04de46fe9ea92f3d0981c548a833fd96adab4153d4b72e77`

## Git freeze

The authoritative checkpoint ZIP does not contain a `.git` repository. Therefore a repository commit/tag cannot be created without inventing Git history.

- freeze commit: `NOT CREATED`
- freeze tag: `NOT CREATED`
- reason: authoritative source artifact is not Git-enabled.
- working-tree status: `NOT APPLICABLE (NO .git)`

Recommended Git metadata if this frozen tree is later imported into the canonical Git repository:

- commit message: `freeze FAZ 3.3 provider architecture v0.1.0`
- tag: `sitescore-providers-v0.1.0`

## Final repository ZIP integrity

Final artifact name: `sitescore-providers-v0.1.0.zip`.

A ZIP cannot truthfully contain its own final SHA-256 inside one of its member files: changing this record to insert that hash changes the ZIP bytes and therefore changes the hash. The authoritative final ZIP SHA-256 is therefore stored in the detached companion file `sitescore-providers-v0.1.0.zip.sha256` and reported with the freeze artifact. This record is part of the hashed ZIP itself.

## Explicitly deferred / not part of frozen FAZ 3.3

The following are **not implemented as part of frozen FAZ 3.3**:

- benchmark acquisition;
- benchmark frame construction;
- ECDF artifacts/calculation;
- normalization;
- `DerivedLocationMetrics` assembly;
- `NormalizedLocationFeatures` assembly;
- COMB-005 road+parking combination policy/implementation;
- `RealDataPipelineResult` orchestration;
- application integration;
- `sitescore-core` adapter/integration;
- empirical calibration and production benchmark validation.

These belong to later work and must preserve the authoritative handoff constraints.

## Final audit decision

All checkpoint locks, production-file integrity, runtime dependency boundary, import boundary, test baselines, provenance/identity/failure-state invariants and scope exclusions are clean.

**FAZ 3.3 PROVIDER ARCHITECTURE — FROZEN**
