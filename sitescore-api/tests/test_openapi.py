from __future__ import annotations

from sitescore_api.app import create_app


def _walk_refs(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "$ref" and isinstance(v, str):
                yield v
            yield from _walk_refs(v)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_refs(item)


def test_required_v1_routes_and_only_checkpoint_scope():
    schema = create_app().openapi()
    paths = schema["paths"]
    assert "post" in paths["/v1/analyses"]
    assert "get" in paths["/v1/analyses/{analysis_id}"]
    assert not any("report" in path for path in paths)
    assert not any("payment" in path for path in paths)
    assert not any("n8n" in path for path in paths)


def test_post_schema_is_discriminated_four_sector_union():
    schema = create_app().openapi()
    post = schema["paths"]["/v1/analyses"]["post"]
    request_schema = post["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema["discriminator"]["propertyName"] == "sector"
    refs = sorted(set(_walk_refs(request_schema)))
    expected = {
        "#/components/schemas/BeautyAnalysisRequest",
        "#/components/schemas/CoffeeAnalysisRequest",
        "#/components/schemas/GymAnalysisRequest",
        "#/components/schemas/RestaurantAnalysisRequest",
    }
    assert expected.issubset(set(refs))


def test_all_external_request_schemas_forbid_extra_fields_and_sector_literals_exact():
    schema = create_app().openapi()
    components = schema["components"]["schemas"]
    request_names = [
        "AddressRequest",
        "OperatingCostsRequest",
        "CoffeeBusinessInputs",
        "RestaurantBusinessInputs",
        "GymBusinessInputs",
        "BeautyBusinessInputs",
        "CoffeeAnalysisRequest",
        "RestaurantAnalysisRequest",
        "GymAnalysisRequest",
        "BeautyAnalysisRequest",
    ]
    for name in request_names:
        assert components[name]["additionalProperties"] is False

    assert components["CoffeeAnalysisRequest"]["properties"]["sector"]["const"] == "coffee"
    assert components["RestaurantAnalysisRequest"]["properties"]["sector"]["const"] == "restaurant"
    assert components["GymAnalysisRequest"]["properties"]["sector"]["const"] == "gym"
    assert components["BeautyAnalysisRequest"]["properties"]["sector"]["const"] == "beauty"


def test_internal_authority_fields_absent_from_public_request_components():
    schema = create_app().openapi()
    rendered = str(schema["components"]["schemas"])
    forbidden = [
        "category_scores",
        "location_score",
        "decision",
        "confidence",
        "analysis_fingerprint",
        "readiness_fingerprint",
        "score_ready",
        "trusted",
        "force",
        "provider_manifest",
        "source_refs",
        "artifact_refs",
    ]
    for name in forbidden:
        assert name not in rendered


def test_stable_error_model_and_503_are_declared():
    schema = create_app().openapi()
    components = schema["components"]["schemas"]
    assert "ErrorResponse" in components
    for path, method in [
        ("/v1/analyses", "post"),
        ("/v1/analyses/{analysis_id}", "get"),
    ]:
        responses = schema["paths"][path][method]["responses"]
        assert "422" in responses
        assert "503" in responses
        refs = set(_walk_refs(responses))
        assert "#/components/schemas/ErrorResponse" in refs
