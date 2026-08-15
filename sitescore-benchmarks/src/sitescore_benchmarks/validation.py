import math,re
SHA=re.compile(r"^[0-9a-f]{64}$")
def text(v,name):
    if not isinstance(v,str) or not v.strip() or v!=v.strip(): raise ValueError(f"{name} must be a canonical non-empty string")
    return v
def sha(v,name):
    if not isinstance(v,str) or not SHA.fullmatch(v): raise ValueError(f"{name} must be lowercase SHA-256")
def finite(v,name):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)): raise ValueError(f"{name} must be finite")
    return float(v)
