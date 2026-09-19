# Checkpoint 3.3-5 Freeze Hardening

## FINAL-001 — graph_artifact_ref excluded from semantic execution identity

`PedestrianGraphCompatibility.graph_artifact_ref` remains an immutable replay/provenance locator.
It is intentionally excluded from `PedestrianGraphCompatibility.identity` and is now also excluded
from `ValhallaExecutionBinding.identity`.

Semantic execution identity remains bound to:
- binding grammar + canonicalization version
- binding id/version
- graph compatibility identity
- graph content hash
- routing-engine manifest identity
- execution-policy identity

Therefore relocating the exact same graph bytes does not change graph compatibility, execution
binding, or routing request fingerprints. Changing graph content, engine/profile semantics, or
execution limits does change them.

This preserves the foundation invariant that storage/artifact locator identity is not semantic
content/execution identity.
