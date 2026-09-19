# Frozen baseline preflight

Checkpoint 3.3-1 is built against the authoritative frozen package:

- `sitescore-data` version: `0.1.0`
- freeze commit: `f03cbb71bd93c5a3afd78b43991e456595a7f75d`
- freeze tag: `sitescore-data-v0.1.0`
- frozen tests: `361/361 PASS`

Runtime compatibility intentionally checks the package version only. Git metadata is not a runtime dependency.

Before publishing or integrating this package, repository-level preflight must verify that the `sitescore-data` source under test is exactly the commit/tag above and that its 361 frozen tests pass. `sitescore-data` must remain unmodified.

`sitescore-providers` may import `sitescore_data`; it must never import `sitescore` or otherwise depend on `sitescore-core`.
