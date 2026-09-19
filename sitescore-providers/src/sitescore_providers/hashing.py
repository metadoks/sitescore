"""Provider-layer canonical hashing and deterministic primitive encoding."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum, StrEnum
import hashlib
import json
from collections.abc import Mapping
from typing import Any

CANONICALIZATION_VERSION = "v1"

from ._validation import require_aware_datetime, require_finite_number


class HashAlgorithm(StrEnum):
    SHA256 = "sha256"


_DIGEST_LENGTH = {HashAlgorithm.SHA256: 64}


@dataclass(frozen=True, slots=True)
class ContentHash:
    algorithm: HashAlgorithm
    digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.algorithm, HashAlgorithm):
            raise TypeError("algorithm must be a HashAlgorithm")
        if not isinstance(self.digest, str):
            raise TypeError("digest must be a string")
        expected = _DIGEST_LENGTH[self.algorithm]
        if len(self.digest) != expected:
            raise ValueError(f"{self.algorithm.value} digest must contain {expected} hex characters")
        if self.digest != self.digest.lower():
            raise ValueError("digest must use lowercase canonical hex")
        if any(ch not in "0123456789abcdef" for ch in self.digest):
            raise ValueError("digest must contain lowercase hexadecimal characters only")

    @classmethod
    def parse(cls, value: str) -> "ContentHash":
        if not isinstance(value, str):
            raise TypeError("hash value must be a string")
        try:
            algorithm_text, digest = value.split(":", 1)
            algorithm = HashAlgorithm(algorithm_text)
        except (ValueError, TypeError) as exc:
            raise ValueError("hash must use a known 'algorithm:digest' grammar") from exc
        return cls(algorithm=algorithm, digest=digest)

    def __str__(self) -> str:
        return f"{self.algorithm.value}:{self.digest}"


def sha256_bytes(content: bytes) -> ContentHash:
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    return ContentHash(HashAlgorithm.SHA256, hashlib.sha256(content).hexdigest())


def _canonical_datetime(value: datetime) -> str:
    require_aware_datetime(value, field_name="datetime")
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def to_canonical_primitive(value: Any) -> Any:
    """Return provider-layer deterministic JSON-compatible primitives.

    This is deliberately separate from ``sitescore_data.serialization``.
    Mapping order is normalized by canonical JSON encoding; mutable input
    containers are accepted but never retained by provider-layer contracts.
    """

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        require_finite_number(value, field_name="canonical value")
        return value
    if isinstance(value, datetime):
        return {"$datetime_utc": _canonical_datetime(value)}
    if isinstance(value, Enum):
        return to_canonical_primitive(value.value)
    if isinstance(value, ContentHash):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return to_canonical_primitive(asdict(value))
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical mappings require string keys")
            out[key] = to_canonical_primitive(item)
        return out
    if isinstance(value, tuple):
        return [to_canonical_primitive(item) for item in value]
    if isinstance(value, list):
        return [to_canonical_primitive(item) for item in value]
    raise TypeError(f"unsupported canonical primitive type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Encode using provider canonicalization grammar ``CANONICALIZATION_VERSION``.

    Any semantics-changing modification to this encoding requires bumping
    ``CANONICALIZATION_VERSION``.
    """
    primitive = to_canonical_primitive(value)
    return json.dumps(
        primitive,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def hash_canonical(value: Any) -> ContentHash:
    return sha256_bytes(canonical_json_bytes(value))
