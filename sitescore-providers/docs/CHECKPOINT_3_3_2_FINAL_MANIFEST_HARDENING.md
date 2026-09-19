# Checkpoint 3.3-2 Final Manifest Hardening

Scope: FINAL-001 trusted Census benchmark/vintage compatibility boundary and FINAL-002 manifest-bound required/optional layer semantics only.

## FINAL-001

`CensusBenchmarkVintageCompatibility` is an immutable trusted deployment/configuration input containing `compatibility_id`, `compatibility_version`, `geocoder_benchmark`, and `geography_vintage`. It is not a cryptographic approval and this package performs no live Census allowlist or auto-discovery.

`CensusGeographyManifest` accepts only `manifest_version`, `compatibility`, and `supported_layers`; benchmark/vintage and compatibility identity/version are derived properties. Its identity commits to the compatibility identity/version, exact benchmark/vintage pair, layer specifications, manifest grammar/version, and provider canonicalization version.

## FINAL-002

`CensusGeographyLayerSpec.required` is a strict bool and is deployment/configuration policy, not an intrinsic `GeographyType` property. Requiredness participates in manifest identity but not in the Census geography HTTP request fingerprint. A required layer with no manifest-authorized response alias produces `ProviderInvariantError`; an optional absent/unrecognized layer is omitted.

No production global Census numeric layer-ID table or response-alias map was introduced.
