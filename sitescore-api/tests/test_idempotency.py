from __future__ import annotations

from copy import deepcopy
from pydantic import TypeAdapter
import pytest

from sitescore_api.errors import InvalidIdempotencyKey
from sitescore_api.idempotency import (
    IDEMPOTENCY_KEY_MAX_BYTES,
    canonical_request_hash,
    canonical_request_json,
    validate_idempotency_key,
)
from sitescore_api.models import AnalysisRequest

ADAPTER = TypeAdapter(AnalysisRequest)


def test_idempotency_key_boundary_is_exact_and_control_free():
    assert validate_idempotency_key("x" * IDEMPOTENCY_KEY_MAX_BYTES) == "x" * IDEMPOTENCY_KEY_MAX_BYTES
    for value in ("", "   ", "bad\nkey", "x" * (IDEMPOTENCY_KEY_MAX_BYTES + 1)):
        with pytest.raises(InvalidIdempotencyKey):
            validate_idempotency_key(value)


def test_canonical_request_hash_is_deterministic_and_payload_only(valid_payloads):
    a = ADAPTER.validate_python(deepcopy(valid_payloads["coffee"]))
    b = ADAPTER.validate_python(deepcopy(valid_payloads["coffee"]))
    assert canonical_request_hash(a) == canonical_request_hash(b)
    assert canonical_request_json(a) == canonical_request_json(b)
    rendered = str(canonical_request_json(a))
    for operational in (
        "request_id",
        "analysis_id",
        "idempotency_key",
        "authorization",
        "task_id",
        "analysis_fingerprint",
    ):
        assert operational not in rendered.lower()


def test_different_validated_intent_changes_hash(valid_payloads):
    a_payload = deepcopy(valid_payloads["coffee"])
    b_payload = deepcopy(valid_payloads["coffee"])
    b_payload["costs"]["monthly_rent"] += 1
    a = ADAPTER.validate_python(a_payload)
    b = ADAPTER.validate_python(b_payload)
    assert canonical_request_hash(a) != canonical_request_hash(b)
