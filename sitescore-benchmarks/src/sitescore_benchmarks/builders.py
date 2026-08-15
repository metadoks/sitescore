from __future__ import annotations
from .contracts import CommercialFrame, LatticeCellArtifact


def derive_lattice_cell(*, lattice_policy, index_i, index_j):
    """Canonical lattice-cell derivation boundary.

    FRAME-H001 intentionally leaves equal-area attestation unresolved in 3.4-2,
    so production canonical lattice-cell generation is unavailable.  This avoids
    manufacturing canonical cells from arbitrary fixture geometry under an
    unresolved lattice.
    """
    if not lattice_policy.is_resolved:
        raise ValueError("canonical lattice-cell derivation unavailable while lattice is unresolved")
    raise NotImplementedError("verified equal-area lattice-cell derivation is calibration/attestation gated")


def build_frame(*, benchmark_geography, boundary_artifact, lattice_policy, membership_policy, eligibility_policy, cells, generated_at=None):
    ordered = tuple(sorted(cells, key=lambda c: c.cell_id))
    dummy = object.__new__(CommercialFrame)
    object.__setattr__(dummy, "benchmark_geography", benchmark_geography)
    object.__setattr__(dummy, "boundary_artifact", boundary_artifact)
    object.__setattr__(dummy, "lattice_policy", lattice_policy)
    object.__setattr__(dummy, "membership_policy", membership_policy)
    object.__setattr__(dummy, "eligibility_policy", eligibility_policy)
    object.__setattr__(dummy, "cells", ordered)
    from .contracts import _frame_state
    state, reasons = _frame_state(dummy)
    return CommercialFrame(
        benchmark_geography,
        boundary_artifact,
        lattice_policy,
        membership_policy,
        eligibility_policy,
        ordered,
        state,
        reasons,
        generated_at,
    )
