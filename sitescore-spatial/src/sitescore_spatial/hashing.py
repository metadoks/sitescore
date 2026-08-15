from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence, Set
from enum import Enum
from typing import Any

SPATIAL_IDENTITY_GRAMMAR = "sitescore-spatial-canonical-json"
SPATIAL_IDENTITY_GRAMMAR_VERSION = "1.0"
HASH_ALGORITHM = "sha256"


def _canon(value: Any) -> Any:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are forbidden")
        return ["float64", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, Enum):
        return ["enum", value.__class__.__name__, _canon(value.value)]
    if isinstance(value, Mapping):
        if any(not isinstance(k, str) for k in value):
            raise TypeError("canonical maps require string keys")
        return ["map", [[k, _canon(value[k])] for k in sorted(value)]]
    if isinstance(value, Set):
        items = [_canon(v) for v in value]
        items.sort(key=lambda x: json.dumps(x, separators=(",", ":"), ensure_ascii=False))
        return ["set", items]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, memoryview)):
        return ["seq", [_canon(v) for v in value]]
    raise TypeError(f"unsupported canonical object: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    envelope = {
        "grammar": SPATIAL_IDENTITY_GRAMMAR,
        "grammar_version": SPATIAL_IDENTITY_GRAMMAR_VERSION,
        "value": _canon(value),
    }
    return json.dumps(envelope, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def semantic_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def content_hash(data: bytes) -> str:
    if not isinstance(data, bytes):
        raise TypeError("content_hash requires bytes")
    return hashlib.sha256(data).hexdigest()
