from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

from .contracts import ProductCode
from .settings import Settings

CATALOG_VERSION = "v1"


class CheckoutProviderUnavailable(RuntimeError):
    pass


class CheckoutInvariantError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProductCatalogEntry:
    product_code: ProductCode
    catalog_version: str
    quantity: int
    currency_expectation: str
    stripe_price_id: str


@dataclass(frozen=True)
class CheckoutResult:
    session_id: str
    url: str
    expires_at: datetime | None
    mode: str
    client_reference_id: str
    metadata: dict[str, str]


class CheckoutGateway(Protocol):
    def create_checkout(self, *, order_id: UUID, email: str, entry: ProductCatalogEntry, provider_idempotency_key: str, success_url: str, cancel_url: str) -> CheckoutResult: ...


def catalog_from_settings(settings: Settings) -> ProductCatalogEntry:
    return ProductCatalogEntry(product_code=ProductCode.LOCATION_REPORT_V1, catalog_version=CATALOG_VERSION, quantity=1, currency_expectation="USD", stripe_price_id=settings.stripe_price_location_report_v1)


def success_url(settings: Settings, order_id: UUID) -> str:
    return f"{settings.success_url_base}?order_id={quote(str(order_id))}&session_id={{CHECKOUT_SESSION_ID}}"


def cancel_url(settings: Settings, order_id: UUID) -> str:
    return f"{settings.cancel_url_base}?order_id={quote(str(order_id))}"


class StripeCheckoutGateway:
    def __init__(self, settings: Settings):
        from stripe import StripeClient
        self._client = StripeClient(settings.stripe_secret_key)
        self._api_version = settings.stripe_api_version

    def create_checkout(self, *, order_id: UUID, email: str, entry: ProductCatalogEntry, provider_idempotency_key: str, success_url: str, cancel_url: str) -> CheckoutResult:
        params = {
            "mode": "payment",
            "ui_mode": "hosted",
            "payment_method_types": ["card"],
            "line_items": [{"price": entry.stripe_price_id, "quantity": entry.quantity}],
            "client_reference_id": str(order_id),
            "customer_email": email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"sitescore_order_id": str(order_id), "sitescore_product_code": entry.product_code.value, "sitescore_catalog_version": entry.catalog_version},
            "payment_intent_data": {"metadata": {"sitescore_order_id": str(order_id), "sitescore_product_code": entry.product_code.value}},
        }
        try:
            session = self._client.v1.checkout.sessions.create(params=params, options={"stripe_version": self._api_version, "idempotency_key": provider_idempotency_key})
        except Exception as exc:
            raise CheckoutProviderUnavailable("checkout provider is unavailable") from exc
        expires_at = None
        raw_expires = getattr(session, "expires_at", None)
        if raw_expires is not None:
            expires_at = datetime.fromtimestamp(int(raw_expires), tz=timezone.utc)
        metadata = dict(getattr(session, "metadata", {}) or {})
        return CheckoutResult(session_id=str(getattr(session, "id", "")), url=str(getattr(session, "url", "")), expires_at=expires_at, mode=str(getattr(session, "mode", "")), client_reference_id=str(getattr(session, "client_reference_id", "")), metadata={str(k): str(v) for k, v in metadata.items()})


def validate_checkout_result(result: CheckoutResult, *, order_id: UUID, entry: ProductCatalogEntry) -> None:
    if not result.session_id.startswith("cs_"):
        raise CheckoutInvariantError("checkout provider returned an invalid session identity")
    if not result.url.startswith("https://"):
        raise CheckoutInvariantError("checkout provider returned an invalid hosted URL")
    if result.mode != "payment":
        raise CheckoutInvariantError("checkout mode binding mismatch")
    if result.client_reference_id != str(order_id):
        raise CheckoutInvariantError("checkout order binding mismatch")
    expected = {"sitescore_order_id": str(order_id), "sitescore_product_code": entry.product_code.value, "sitescore_catalog_version": entry.catalog_version}
    for key, value in expected.items():
        if result.metadata.get(key) != value:
            raise CheckoutInvariantError("checkout metadata binding mismatch")
