import hashlib
import json
from dataclasses import asdict
from enum import Enum
from typing import Any

from sitescore.schemas.analysis import AnalysisInput
from sitescore.schemas.metadata import ModelVersions


def _normalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(value.items())
        }

    if isinstance(value, (list, tuple)):
        return [
            _normalize(item)
            for item in value
        ]

    return value


def generate_analysis_fingerprint(
    data: AnalysisInput,
    versions: ModelVersions,
) -> str:
    payload = {
        "input": _normalize(asdict(data)),
        "model_versions": _normalize(asdict(versions)),
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()

    return digest