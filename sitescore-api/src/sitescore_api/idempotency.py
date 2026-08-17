from __future__ import annotations

from hashlib import sha256
import json
from pydantic import BaseModel
from .errors import IdempotencyKeyRequired, InvalidIdempotencyKey

IDEMPOTENCY_KEY_MAX_BYTES = 200


def validate_idempotency_key(value: str | None) -> str:
    if value is None:
        raise IdempotencyKeyRequired()
    if not isinstance(value, str) or not value.strip():
        raise InvalidIdempotencyKey()
    encoded = value.encode("utf-8")
    if len(encoded) > IDEMPOTENCY_KEY_MAX_BYTES:
        raise InvalidIdempotencyKey()
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise InvalidIdempotencyKey()
    return value


def canonical_request_json(model: BaseModel) -> dict[str, object]:
    value = model.model_dump(mode="json", exclude_none=False)
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return json.loads(encoded)


def canonical_request_hash(model: BaseModel) -> str:
    encoded = json.dumps(
        model.model_dump(mode="json", exclude_none=False),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
