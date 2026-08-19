from __future__ import annotations
import pytest
from sitescore_commerce.settings import ConfigurationError, Settings

def base_env(monkeypatch):
    monkeypatch.setenv("SITESCORE_COMMERCE_DATABASE_URL","postgresql+psycopg://localhost/test")
    monkeypatch.setenv("STRIPE_SECRET_KEY","sk_test_not-real")
    monkeypatch.setenv("STRIPE_PRICE_LOCATION_REPORT_V1","price_1234567890")
    monkeypatch.setenv("COMMERCE_SUCCESS_URL_BASE","https://app.example/success")
    monkeypatch.setenv("COMMERCE_CANCEL_URL_BASE","https://app.example/cancel")
    monkeypatch.setenv("STRIPE_API_VERSION","2026-07-29.dahlia")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET","test-signing-secret")
    monkeypatch.setenv("STRIPE_EXPECTED_LIVEMODE","false")
    monkeypatch.setenv("SITESCORE_API_BASE_URL","https://sitescore.example")
    monkeypatch.setenv("SITESCORE_API_SERVICE_KEY","sitescore-service-key-test")
    monkeypatch.setenv("SITESCORE_API_TARGET_ID","production-v1")
    monkeypatch.setenv("SITESCORE_API_TIMEOUT_SECONDS","10")
    monkeypatch.setenv("COMMERCE_AUTOMATION_API_KEY","automation-key-test-0123456789")

def test_production_redirects_and_version_pin(monkeypatch):
    base_env(monkeypatch); s=Settings.from_env(); assert s.stripe_api_version=="2026-07-29.dahlia" and s.stripe_expected_livemode is False and s.stripe_webhook_secret=="test-signing-secret"; assert s.sitescore_api_base_url=="https://sitescore.example" and s.sitescore_api_target_id=="production-v1" and s.sitescore_api_timeout_seconds==10

@pytest.mark.parametrize("name,value",[("COMMERCE_SUCCESS_URL_BASE","https://user:pass@app.example/success"),("COMMERCE_CANCEL_URL_BASE","https://app.example/cancel#fragment"),("COMMERCE_SUCCESS_URL_BASE","https://app.example/success?paid=true"),("COMMERCE_CANCEL_URL_BASE","http://evil.example/cancel")])
def test_unsafe_redirect_config_fails_closed(monkeypatch,name,value):
    base_env(monkeypatch); monkeypatch.setenv(name,value)
    with pytest.raises(ConfigurationError): Settings.from_env()

def test_api_version_override_fails_closed(monkeypatch):
    base_env(monkeypatch); monkeypatch.setenv("STRIPE_API_VERSION","account-default")
    with pytest.raises(ConfigurationError): Settings.from_env()

@pytest.mark.parametrize("value",["","maybe","live-ish"])
def test_webhook_livemode_config_fails_closed(monkeypatch,value):
    base_env(monkeypatch); monkeypatch.setenv("STRIPE_EXPECTED_LIVEMODE",value)
    with pytest.raises(ConfigurationError): Settings.from_env()

def test_webhook_secret_is_required(monkeypatch):
    base_env(monkeypatch); monkeypatch.delenv("STRIPE_WEBHOOK_SECRET")
    with pytest.raises(ConfigurationError): Settings.from_env()

@pytest.mark.parametrize("value",["http://sitescore.example","https://user:pass@sitescore.example","https://sitescore.example/v1","https://sitescore.example?secret=x","https://sitescore.example/#x"])
def test_sitescore_target_config_fails_closed(monkeypatch,value):
    base_env(monkeypatch); monkeypatch.setenv("SITESCORE_API_BASE_URL",value)
    with pytest.raises(ConfigurationError): Settings.from_env()

@pytest.mark.parametrize("value",["0","-1","61","nan","abc"])
def test_sitescore_timeout_config_fails_closed(monkeypatch,value):
    base_env(monkeypatch); monkeypatch.setenv("SITESCORE_API_TIMEOUT_SECONDS",value)
    with pytest.raises(ConfigurationError): Settings.from_env()

@pytest.mark.parametrize("name",["SITESCORE_API_BASE_URL","SITESCORE_API_SERVICE_KEY","SITESCORE_API_TARGET_ID","COMMERCE_AUTOMATION_API_KEY"])
def test_fulfillment_server_configuration_is_required(monkeypatch,name):
    base_env(monkeypatch); monkeypatch.delenv(name)
    with pytest.raises(ConfigurationError): Settings.from_env()
