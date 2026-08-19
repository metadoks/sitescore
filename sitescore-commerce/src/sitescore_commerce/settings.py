from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

STRIPE_API_VERSION = "2026-07-29.dahlia"


class ConfigurationError(RuntimeError):
    pass


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"required configuration is unavailable: {name}")
    return value


def _validate_price_id(value: str) -> str:
    if not value.startswith("price_") or len(value) < 10 or not value.replace("_", "").isalnum():
        raise ConfigurationError("configured Stripe Price ID is malformed")
    return value


def _validate_redirect_base(value: str, *, environment: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigurationError("redirect URL must be absolute http/https")
    if parsed.username or parsed.password:
        raise ConfigurationError("redirect URL must not contain embedded credentials")
    if parsed.fragment:
        raise ConfigurationError("redirect URL must not contain a fragment")
    if parsed.query:
        raise ConfigurationError("redirect URL base must not contain a query")
    if environment == "production" and parsed.scheme != "https":
        raise ConfigurationError("production redirect URL must use https")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ConfigurationError("http redirect URL is permitted only for local test/development")
    return value.rstrip("?")


def _parse_bool(name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True)
class Settings:
    database_url: str
    stripe_secret_key: str
    stripe_price_location_report_v1: str
    success_url_base: str
    cancel_url_base: str
    stripe_webhook_secret: str = "whsec_test_placeholder"
    stripe_expected_livemode: bool = False
    environment: str = "production"
    stripe_api_version: str = STRIPE_API_VERSION

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("COMMERCE_ENV", "production").strip().lower()
        if environment not in {"production", "development", "test"}:
            raise ConfigurationError("COMMERCE_ENV must be production, development, or test")
        configured_api_version = os.getenv("STRIPE_API_VERSION", STRIPE_API_VERSION).strip()
        if configured_api_version != STRIPE_API_VERSION:
            raise ConfigurationError(f"STRIPE_API_VERSION must be pinned to {STRIPE_API_VERSION}")
        return cls(
            database_url=_require("SITESCORE_COMMERCE_DATABASE_URL"),
            stripe_secret_key=_require("STRIPE_SECRET_KEY"),
            stripe_price_location_report_v1=_validate_price_id(_require("STRIPE_PRICE_LOCATION_REPORT_V1")),
            success_url_base=_validate_redirect_base(_require("COMMERCE_SUCCESS_URL_BASE"), environment=environment),
            cancel_url_base=_validate_redirect_base(_require("COMMERCE_CANCEL_URL_BASE"), environment=environment),
            stripe_webhook_secret=_require("STRIPE_WEBHOOK_SECRET"),
            stripe_expected_livemode=_parse_bool("STRIPE_EXPECTED_LIVEMODE", _require("STRIPE_EXPECTED_LIVEMODE")),
            environment=environment,
            stripe_api_version=STRIPE_API_VERSION,
        )
