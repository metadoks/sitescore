from __future__ import annotations

import math
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


def _validate_http_base(value: str, *, environment: str, label: str, allow_query: bool = False) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigurationError(f"{label} must be absolute http/https")
    if parsed.username or parsed.password:
        raise ConfigurationError(f"{label} must not contain embedded credentials")
    if parsed.fragment:
        raise ConfigurationError(f"{label} must not contain a fragment")
    if parsed.query and not allow_query:
        raise ConfigurationError(f"{label} must not contain a query")
    if environment == "production" and parsed.scheme != "https":
        raise ConfigurationError(f"production {label} must use https")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ConfigurationError(f"http {label} is permitted only for local test/development")
    return value.rstrip("/")


def _validate_redirect_base(value: str, *, environment: str) -> str:
    return _validate_http_base(value, environment=environment, label="redirect URL")


def _validate_sitescore_base(value: str, *, environment: str) -> str:
    parsed = urlparse(value)
    normalized = _validate_http_base(value, environment=environment, label="SiteScore API base URL")
    if parsed.path not in {"", "/"}:
        raise ConfigurationError("SiteScore API base URL must not contain a path")
    return normalized


def _parse_bool(name: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


def _parse_timeout(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigurationError("SITESCORE_API_TIMEOUT_SECONDS must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0 or parsed > 60:
        raise ConfigurationError("SITESCORE_API_TIMEOUT_SECONDS must be >0 and <=60")
    return parsed


def _validate_secret(name: str, value: str, *, minimum: int = 16) -> str:
    if len(value.encode("utf-8")) < minimum:
        raise ConfigurationError(f"{name} is too short")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    stripe_secret_key: str
    stripe_price_location_report_v1: str
    success_url_base: str
    cancel_url_base: str
    environment: str = "production"
    stripe_webhook_secret: str = ""
    stripe_expected_livemode: bool = False
    stripe_api_version: str = STRIPE_API_VERSION
    sitescore_api_base_url: str = "https://sitescore.invalid"
    sitescore_api_service_key: str = ""
    sitescore_api_target_id: str = "unconfigured"
    sitescore_api_timeout_seconds: float = 10.0
    commerce_automation_api_key: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("COMMERCE_ENV", "production").strip().lower()
        if environment not in {"production", "development", "test"}:
            raise ConfigurationError("COMMERCE_ENV must be production, development, or test")
        configured_api_version = os.getenv("STRIPE_API_VERSION", STRIPE_API_VERSION).strip()
        if configured_api_version != STRIPE_API_VERSION:
            raise ConfigurationError(f"STRIPE_API_VERSION must be pinned to {STRIPE_API_VERSION}")
        sitescore_target_id = _require("SITESCORE_API_TARGET_ID")
        if len(sitescore_target_id.encode("utf-8")) > 128:
            raise ConfigurationError("SITESCORE_API_TARGET_ID exceeds 128 UTF-8 bytes")
        return cls(
            database_url=_require("SITESCORE_COMMERCE_DATABASE_URL"),
            stripe_secret_key=_require("STRIPE_SECRET_KEY"),
            stripe_price_location_report_v1=_validate_price_id(_require("STRIPE_PRICE_LOCATION_REPORT_V1")),
            success_url_base=_validate_redirect_base(_require("COMMERCE_SUCCESS_URL_BASE"), environment=environment),
            cancel_url_base=_validate_redirect_base(_require("COMMERCE_CANCEL_URL_BASE"), environment=environment),
            environment=environment,
            stripe_webhook_secret=_require("STRIPE_WEBHOOK_SECRET"),
            stripe_expected_livemode=_parse_bool("STRIPE_EXPECTED_LIVEMODE", _require("STRIPE_EXPECTED_LIVEMODE")),
            stripe_api_version=STRIPE_API_VERSION,
            sitescore_api_base_url=_validate_sitescore_base(_require("SITESCORE_API_BASE_URL"), environment=environment),
            sitescore_api_service_key=_validate_secret("SITESCORE_API_SERVICE_KEY", _require("SITESCORE_API_SERVICE_KEY")),
            sitescore_api_target_id=sitescore_target_id,
            sitescore_api_timeout_seconds=_parse_timeout(os.getenv("SITESCORE_API_TIMEOUT_SECONDS", "10")),
            commerce_automation_api_key=_validate_secret("COMMERCE_AUTOMATION_API_KEY", _require("COMMERCE_AUTOMATION_API_KEY"), minimum=24),
        )
