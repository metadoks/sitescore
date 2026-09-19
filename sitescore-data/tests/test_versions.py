from sitescore_data import version


def test_data_layer_version_names_are_explicit_and_present() -> None:
    assert version.PACKAGE_VERSION == "0.1.0"
    assert version.DATA_SCHEMA_VERSION == "1.0"
    assert version.BENCHMARK_SCHEMA_VERSION == "1.0"
    assert version.DATA_FEATURE_CONTRACT_VERSION == "1.0"
    assert version.READINESS_CONTRACT_VERSION == "1.0"
    assert version.DATA_SERIALIZATION_VERSION == "1.0"
