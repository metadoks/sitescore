from enum import Enum

class ResolutionState(str, Enum):
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"

class BoundaryMembershipState(str, Enum):
    MEMBER = "MEMBER"
    NON_MEMBER = "NON_MEMBER"
    UNRESOLVED = "UNRESOLVED"

class EligibilityState(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"

class EvidenceDisposition(str, Enum):
    POSITIVE = "POSITIVE"
    EXPLICIT_EXCLUSION = "EXPLICIT_EXCLUSION"
    UNRESOLVED = "UNRESOLVED"

class ApplicabilityState(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNRESOLVED = "UNRESOLVED"

class FrameState(str, Enum):
    STRUCTURAL_ONLY = "STRUCTURAL_ONLY"
    PRODUCTION_READY = "PRODUCTION_READY"
    UNRESOLVED = "UNRESOLVED"

class CellShape(str, Enum):
    SQUARE = "SQUARE"

class DiagnosticState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNRESOLVED = "UNRESOLVED"
