import pytest

from sitescore_spatial import canonical_json_bytes, semantic_hash


def test_mapping_order_independent():
    assert semantic_hash({"a": 1, "b": 2}) == semantic_hash({"b": 2, "a": 1})


def test_bool_does_not_collapse_into_int():
    assert semantic_hash(True) != semantic_hash(1)


def test_int_does_not_collapse_into_float():
    assert semantic_hash(1) != semantic_hash(1.0)


def test_set_order_independent():
    assert semantic_hash({"x", "y"}) == semantic_hash({"y", "x"})


def test_non_string_mapping_key_rejected():
    with pytest.raises(TypeError):
        canonical_json_bytes({1: "x"})


@pytest.mark.parametrize("x", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_rejected(x):
    with pytest.raises(ValueError):
        semantic_hash(x)


def test_unsupported_object_rejected():
    with pytest.raises(TypeError):
        semantic_hash(object())
