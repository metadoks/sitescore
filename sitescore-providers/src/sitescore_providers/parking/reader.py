"""Backend-neutral parking source reader boundary.

Native OSM PBF/XML/municipal formats are decoded by deployment adapters into
strict row mappings. The provider package does not select a GIS/PBF dependency.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from .models import ParkingSourceManifest


@runtime_checkable
class ParkingRecordReader(Protocol):
    def read_records(
        self,
        *,
        content: bytes,
        manifest: ParkingSourceManifest,
    ) -> tuple[Mapping[str, Any], ...]:
        """Decode exact pinned source bytes into parking row mappings."""
        ...
