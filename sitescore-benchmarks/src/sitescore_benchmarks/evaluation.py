from .contracts import CommercialEligibilityResult, _eligibility, FrameBoundaryMembership, _membership

def evaluate_commercial_eligibility(bundle, policy):
    state,reasons=_eligibility(bundle,policy)
    return CommercialEligibilityResult(bundle,policy,state,reasons)

def evaluate_boundary_membership(full_cell_geometry,boundary_artifact,membership_policy,diagnostic_evidence=None):
    state,reasons=_membership(membership_policy,diagnostic_evidence)
    return FrameBoundaryMembership(full_cell_geometry,boundary_artifact,membership_policy,diagnostic_evidence,state,reasons)
