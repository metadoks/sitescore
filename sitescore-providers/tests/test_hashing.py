from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from sitescore_providers import CANONICALIZATION_VERSION, ContentHash, HashAlgorithm, canonical_json_bytes, hash_canonical, sha256_bytes


def test_hash_canonicalization_and_string_round_trip():
    value = sha256_bytes(b"abc")
    assert str(value) == "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert ContentHash.parse(str(value)) == value


@pytest.mark.parametrize(
    "value",
    [
        "sha1:" + "a" * 40,
        "sha256:" + "A" * 64,
        "sha256:" + "g" * 64,
        "sha256:" + "a" * 63,
        "nocolon",
    ],
)
def test_malformed_hash_rejected(value):
    with pytest.raises(ValueError):
        ContentHash.parse(value)


def test_unknown_algorithm_type_rejected():
    with pytest.raises(TypeError):
        ContentHash("sha256", "a" * 64)  # type: ignore[arg-type]


def test_canonical_json_mapping_order_independent():
    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes({"a": 1, "b": 2})
    assert hash_canonical({"b": 2, "a": 1}) == hash_canonical({"a": 1, "b": 2})


def test_aware_datetimes_are_normalized_to_utc():
    a = datetime(2026, 8, 12, 16, tzinfo=timezone.utc)
    b = datetime.fromisoformat("2026-08-12T19:00:00+03:00")
    assert hash_canonical({"t": a}) == hash_canonical({"t": b})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numbers_rejected(value):
    with pytest.raises(ValueError):
        hash_canonical({"x": value})


def test_non_string_mapping_keys_rejected():
    with pytest.raises(TypeError):
        canonical_json_bytes({1: "x"})


def test_unsupported_objects_rejected():
    with pytest.raises(TypeError):
        canonical_json_bytes(object())


def test_utc_equivalent_datetimes_have_same_canonical_bytes():
    a = datetime(2026, 8, 12, 16, tzinfo=timezone.utc)
    b = datetime.fromisoformat("2026-08-12T19:00:00+03:00")
    assert canonical_json_bytes({"t": a}) == canonical_json_bytes({"t": b})


def test_unicode_utf8_is_deterministic_and_not_ascii_escaped():
    value = {"şehir": "İstanbul", "symbol": "→"}
    encoded = canonical_json_bytes(value)
    assert encoded == canonical_json_bytes({"symbol": "→", "şehir": "İstanbul"})
    assert "İstanbul".encode("utf-8") in encoded
    assert "→".encode("utf-8") in encoded


def test_bool_and_int_have_distinct_canonical_semantics():
    assert canonical_json_bytes(True) != canonical_json_bytes(1)
    assert hash_canonical({"x": True}) != hash_canonical({"x": 1})


def test_canonicalization_version_is_explicit():
    assert CANONICALIZATION_VERSION == "v1"


def test_content_hash_is_immutable():
    value = ContentHash(HashAlgorithm.SHA256, "a" * 64)
    with pytest.raises(FrozenInstanceError):
        value.digest = "b" * 64  # type: ignore[misc]
