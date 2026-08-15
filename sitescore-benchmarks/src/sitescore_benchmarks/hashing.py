from __future__ import annotations
import hashlib, json, math
from enum import Enum
from dataclasses import is_dataclass, fields

GRAMMAR = "sitescore-benchmarks-canonical-json"
GRAMMAR_VERSION = "1.0"

def _canon(v):
    if v is None or isinstance(v, (str, bool, int)):
        return v
    if isinstance(v, float):
        if not math.isfinite(v):
            raise ValueError("non-finite number")
        return {"$float": v.hex()}
    if isinstance(v, Enum): return v.value
    if isinstance(v, bytes): return {"$bytes": v.hex()}
    if isinstance(v, tuple): return [_canon(x) for x in v]
    if isinstance(v, list): return [_canon(x) for x in v]
    if isinstance(v, (set, frozenset)):
        vals=[_canon(x) for x in v]
        return sorted(vals, key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    if isinstance(v, dict):
        if any(not isinstance(k,str) for k in v): raise TypeError("mapping keys must be strings")
        return {k:_canon(v[k]) for k in sorted(v)}
    if hasattr(v, "semantic_record"):
        return _canon(v.semantic_record())
    if is_dataclass(v):
        return {f.name:_canon(getattr(v,f.name)) for f in fields(v)}
    raise TypeError(f"unsupported canonical value: {type(v).__name__}")

def canonical_json_bytes(value)->bytes:
    payload={"grammar":GRAMMAR,"version":GRAMMAR_VERSION,"value":_canon(value)}
    return json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def semantic_hash(value)->str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
