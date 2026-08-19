from __future__ import annotations
import pytest
from sitescore_commerce.settings import ConfigurationError, Settings
def base_env(monkeypatch):
    monkeypatch.setenv("SITESCORE_COMMERCE_DATABASE_URL","postgresql+psycopg://localhost/test"); monkeypatch.setenv("STRIPE_SECRET_KEY","sk_test_not-real"); monkeypatch.setenv("STRIPE_PRICE_LOCATION_REPORT_V1","price_1234567890"); monkeypatch.setenv("COMMERCE_SUCCESS_URL_BASE","https://app.example/success"); monkeypatch.setenv("COMMERCE_CANCEL_URL_BASE","https://app.example/cancel"); monkeypatch.setenv("STRIPE_API_VERSION","2026-07-29.dahlia")
def test_production_redirects_and_version_pin(monkeypatch): base_env(monkeypatch); assert Settings.from_env().stripe_api_version=="2026-07-29.dahlia"
@pytest.mark.parametrize("name,value",[("COMMERCE_SUCCESS_URL_BASE","https://user:pass@app.example/success"),("COMMERCE_CANCEL_URL_BASE","https://app.example/cancel#fragment"),("COMMERCE_SUCCESS_URL_BASE","https://app.example/success?paid=true"),("COMMERCE_CANCEL_URL_BASE","http://evil.example/cancel")])
def test_unsafe_redirect_config_fails_closed(monkeypatch,name,value):
    base_env(monkeypatch); monkeypatch.setenv(name,value)
    with pytest.raises(ConfigurationError): Settings.from_env()
def test_api_version_override_fails_closed(monkeypatch):
    base_env(monkeypatch); monkeypatch.setenv("STRIPE_API_VERSION","account-default")
    with pytest.raises(ConfigurationError): Settings.from_env()
