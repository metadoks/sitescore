from __future__ import annotations
import hashlib, json, math
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum

GRAMMAR = "sitescore-metrics-canonical-json"
GRAMMAR_VERSION = "1.0"

def _canon(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not canonical")
        return {"$float64": value.hex()}
    if isinstance(value, Enum):
        return {"$enum": f"{type(value).__module__}.{type(value).__qualname__}", "value": value.value}
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetimes must be timezone-aware")
        return {"$datetime": value.isoformat()}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, tuple):
        return [_canon(v) for v in value]
    if isinstance(value, list):
        return [_canon(v) for v in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("canonical mapping keys must be strings")
        return {k: _canon(value[k]) for k in sorted(value)}
    if is_dataclass(value):
        result = {"$type": f"{type(value).__module__}.{type(value).__qualname__}"}
        for f in fields(value):
            if f.name in {"generated_at", "retrieved_at"}:
                continue
            field_value = getattr(value, f.name)
            if f.name in {"source_refs", "reason_codes"} and isinstance(field_value, tuple):
                field_value = tuple(sorted(field_value))
            result[f.name] = _canon(field_value)
        return result
    raise TypeError(f"unsupported canonical value: {type(value)!r}")

def semantic_hash(record) -> str:
    payload = {"grammar": GRAMMAR, "version": GRAMMAR_VERSION, "record": _canon(record)}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()
