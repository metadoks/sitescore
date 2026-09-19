from __future__ import annotations

import pytest

from sitescore_api.outcomes import CanonicalCompletedOutcome, CanonicalNotScoreReadyOutcome


def test_terminal_capability_constructors_are_closed():
    with pytest.raises(TypeError, match="server-factory owned"):
        CanonicalNotScoreReadyOutcome()
    with pytest.raises(TypeError, match="server-factory owned"):
        CanonicalCompletedOutcome()


def test_plain_json_or_fingerprint_cannot_construct_completed_authority():
    forged = object.__new__(CanonicalCompletedOutcome)
    object.__setattr__(forged, "application_analysis_result", {"analysis_fingerprint": "forged"})
    object.__setattr__(forged, "result_body", {"score": 100})
    from sitescore_api.outcomes import require_canonical_completed_outcome
    with pytest.raises((TypeError, ValueError)):
        require_canonical_completed_outcome(forged)
