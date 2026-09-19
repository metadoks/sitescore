from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import os
import subprocess


def _assert_non_root() -> None:
    assert os.getuid() != 0, "runtime must not execute as root"
    assert os.getgid() != 0, "runtime group must not be root"


def _import_all(names: tuple[str, ...]) -> None:
    for name in names:
        importlib.import_module(name)


def verify_api() -> None:
    _assert_non_root()
    _import_all(
        (
            "sitescore_api",
            "sitescore_report",
            "weasyprint",
            "matplotlib",
            "shapely",
            "pyproj",
            "celery",
            "uvicorn",
        )
    )
    expected = {
        "Jinja2": "3.1.6",
        "matplotlib": "3.11.1",
        "weasyprint": "69.0",
        "uvicorn": "0.52.1",
    }
    for distribution, version in expected.items():
        actual = importlib.metadata.version(distribution)
        assert actual == version, f"{distribution}: expected {version}, got {actual}"
    result = subprocess.run(
        ["fc-match", "DejaVu Sans"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "DejaVu" in result.stdout, result.stdout


def verify_commerce() -> None:
    _assert_non_root()
    _import_all(("sitescore_commerce", "uvicorn"))
    assert importlib.metadata.version("uvicorn") == "0.52.1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=("api", "commerce"))
    args = parser.parse_args()
    if args.role == "api":
        verify_api()
    else:
        verify_commerce()


if __name__ == "__main__":
    main()
