from __future__ import annotations

from sitescore_commerce.api import create_app


EXPECTED_RUNTIME_SURFACE = {
    ("POST", "/v1/orders"),
    ("POST", "/v1/webhooks/stripe"),
    ("POST", "/v1/automation/orders/{order_id}/advance"),
    ("POST", "/v1/automation/orders/{order_id}/deliver"),
    ("GET", "/v1/automation/orders/{order_id}"),
    ("POST", "/v1/automation/recovery/run"),
    ("GET", "/d/{opaque_token}"),
}


def _constructed_app():
    # Runtime route registration does not require provider calls. Inject the three
    # pre-existing constructor boundaries so environment-backed production services
    # are not built while inspecting the authoritative resolved FastAPI route table.
    return create_app(
        service=object(),
        webhook_service=object(),
        fulfillment_service=object(),
    )


def test_resolved_runtime_http_surface_is_exactly_the_authorized_seven_routes():
    app = _constructed_app()
    resolved = {
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or set())
    }
    assert resolved == EXPECTED_RUNTIME_SURFACE
    assert len(app.routes) == 7


def test_framework_documentation_openapi_and_oauth_helper_routes_are_absent():
    app = _constructed_app()
    paths = {route.path for route in app.routes}
    assert "/openapi.json" not in paths
    assert "/docs" not in paths
    assert "/redoc" not in paths
    assert "/docs/oauth2-redirect" not in paths
