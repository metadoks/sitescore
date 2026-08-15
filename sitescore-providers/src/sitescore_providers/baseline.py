"""Runtime package-version guard for the frozen SiteScore data dependency."""

from __future__ import annotations

from sitescore_data import PACKAGE_VERSION as SITESCORE_DATA_PACKAGE_VERSION

EXPECTED_SITESCORE_DATA_VERSION = "0.1.0"
EXPECTED_SITESCORE_DATA_COMMIT = "f03cbb71bd93c5a3afd78b43991e456595a7f75d"
EXPECTED_SITESCORE_DATA_TAG = "sitescore-data-v0.1.0"
EXPECTED_SITESCORE_DATA_TESTS = 361


def assert_sitescore_data_compatibility() -> None:
    """Fail fast on an incompatible installed data-contract package version.

    Git commit/tag verification remains a repository preflight and is
    intentionally not required at runtime.
    """

    if SITESCORE_DATA_PACKAGE_VERSION != EXPECTED_SITESCORE_DATA_VERSION:
        raise RuntimeError(
            "incompatible sitescore-data package: "
            f"expected {EXPECTED_SITESCORE_DATA_VERSION}, got {SITESCORE_DATA_PACKAGE_VERSION}"
        )
