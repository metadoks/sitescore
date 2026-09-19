# Checkpoint 3.3-2 Identity / Manifest Hardening Audit

## Scope

Source-level hardening only. No Checkpoint 3.3-3 work.

## AUDIT-001 — Vintage-specific layer identity

Before hardening, `CensusGeographyLayerSpec` contained only `geography_type` and
`response_keys`, and the client incorrectly serialized response aliases into the
Census `layers` request parameter. Core/optional response aliases were also held
in global production constants.

After hardening each manifest-owned layer spec contains:

- provider-independent `GeographyType`
- exact numeric `request_layer_id` for this approved manifest configuration
- accepted response `response_keys`/aliases for this configuration

The manifest identity commits to all three. There is no production global table
of Census numeric layer IDs. The geography request serializes only the exact
manifest layer IDs.

## AUDIT-002 — Benchmark / vintage compatibility

`CensusGeographyManifest` now requires `compatibility_id` and
`compatibility_version`. These fields identify the configuration decision that
approves the exact `geocoder_benchmark` + `geography_vintage` pair. They are
included in manifest identity.

There is deliberately no hard-coded live Census allowlist and no automatic
`Current`/latest discovery. Constructing a manifest is an explicit configuration
approval act; response benchmark/vintage equality checks remain unchanged.

## AUDIT-003 — Operation-specific request fingerprints

Single-address geocoding fingerprints commit only to the semantic provider
request: address fields + pinned geocoder benchmark, plus the generic request
operation/policy identity supplied by the foundation fingerprint builder.
Geography vintage, manifest version, compatibility identity, and layer config do
not affect the geocode fingerprint because they are not sent to `/locations/address`.

Coordinate geography lookup fingerprints commit to latitude, longitude,
benchmark, vintage, and the exact requested Census layer IDs. Manifest/pipeline
metadata that is not part of the provider request is excluded.

## AUDIT-004 — Response aliases

The parser was already manifest-driven. Hardening removed the global production
alias constants, so accepted aliases are now supplied only by the exact layer
specs inside the manifest. Unknown aliases are not guessed or mapped. Changing
an accepted alias changes manifest identity.
