# sitescore-data

Typed, immutable real-data contracts and deterministic validation boundaries for SiteScore.

## Frozen architecture baseline

**FAZ 3.2 CONTRACT ARCHITECTURE — FROZEN**

- Package version: `0.1.0`
- Runtime dependencies: `[]`
- `sitescore_data` must not import `sitescore`
- Provider connectors/builders are not part of this package freeze.
- Category aggregation and core integration belong to the future `sitescore-app` boundary.

See [`docs/FAZ3_2_FREEZE_RECORD.md`](docs/FAZ3_2_FREEZE_RECORD.md) for the complete freeze record, locked checkpoints, final fixes, and deferred-by-design items.

## Canonical test command

```bash
PYTHONPATH=src pytest -o addopts='' -q
```
