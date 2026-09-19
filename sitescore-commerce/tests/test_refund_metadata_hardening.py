from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest

from sitescore_commerce.db import CommerceStore, OrderRow
from sitescore_commerce.fulfillment import (
    AnalysisEvidence,
    AutomationStatus,
    FulfillmentService,
    FulfillmentStore,
    PaymentIntentEvidence,
    RefundEvidence,
    RefundOperationRow,
)
from sitescore_commerce.fulfillment_runtime import FulfillmentRuntimeService
from test_fulfillment_authority import FakeRefunds, FakeSiteScore, FakeStore, operation, settings
from test_fulfillment_postgres import migrate, paid_order, settings as postgres_settings

DATABASE_URL = os.getenv("SITESCORE_COMMERCE_DATABASE_URL")


def _expected_metadata(order_id: UUID) -> dict[str, str]:
    return {
        "sitescore_order_id": str(order_id),
        "sitescore_refund_operation": "stripe_full_refund_v1",
        "sitescore_refund_reason": "analysis_failed",
    }


def _mutated_metadata(order_id: UUID, mutation: str) -> dict[str, str]:
    metadata = _expected_metadata(order_id)
    if mutation == "wrong_order":
        metadata["sitescore_order_id"] = str(uuid4())
    elif mutation == "wrong_operation":
        metadata["sitescore_refund_operation"] = "stripe_full_refund_v2"
    elif mutation == "wrong_reason":
        metadata["sitescore_refund_reason"] = "analysis_timed_out"
    elif mutation == "partial":
        metadata = {"sitescore_order_id": str(order_id)}
    else:
        raise AssertionError(f"unknown mutation: {mutation}")
    return metadata


def _unit_service(service_type: type[FulfillmentService], metadata: dict[str, str]):
    order_id = uuid4()
    analysis_id = uuid4()
    store = FakeStore(
        AutomationStatus(
            order_id,
            "fulfillment_in_progress",
            "paid",
            "analysis_failed",
            True,
            False,
            "refund",
        ),
        operation(order_id, analysis_id=analysis_id, analysis_state="failed"),
    )
    sitescore = FakeSiteScore()
    sitescore.analysis = AnalysisEvidence(analysis_id, "failed")
    refunds = FakeRefunds()
    refunds.pi = PaymentIntentEvidence(
        "pi_paid",
        1000,
        "USD",
        False,
        {
            "sitescore_order_id": str(order_id),
            "sitescore_product_code": "location_report_v1",
        },
    )
    refunds.existing = (
        RefundEvidence(
            "re_existing",
            "pi_paid",
            1000,
            "USD",
            "succeeded",
            metadata,
        ),
    )
    return service_type(settings(), store, sitescore, refunds), store, refunds


@pytest.mark.parametrize("service_type", [FulfillmentService, FulfillmentRuntimeService])
@pytest.mark.parametrize("mutation", ["wrong_order", "wrong_operation", "wrong_reason", "partial"])
def test_reserved_sitescore_metadata_mismatch_never_becomes_external_full_in_any_service_path(service_type, mutation):
    order_id = uuid4()
    metadata = _mutated_metadata(order_id, mutation)
    service, store, refunds = _unit_service(service_type, metadata)
    # Rebind metadata to the actual service order while preserving the requested mutation.
    metadata = _mutated_metadata(store.current.order_id, mutation)
    refunds.existing = (
        RefundEvidence("re_existing", "pi_paid", 1000, "USD", "succeeded", metadata),
    )

    result = service.advance(store.current.order_id)

    assert result.order_state == "attention_required"
    assert result.payment_state == "refund_failed"
    assert result.fulfillment_state == "analysis_failed"
    assert not any(call[0] == "create" for call in refunds.calls)
    assert not any(event[0] == "bind_refund" for event in store.events)
    assert any(event[0] == "attention" and event[1] == "conflicting_refund_metadata" for event in store.events)


@pytest.mark.parametrize("service_type", [FulfillmentService, FulfillmentRuntimeService])
def test_truly_unattributed_external_full_refund_still_reconciles_without_second_refund(service_type):
    service, store, refunds = _unit_service(service_type, {})

    result = service.advance(store.current.order_id)

    assert result.order_state == "refunded"
    assert result.payment_state == "refunded"
    assert not any(call[0] == "create" for call in refunds.calls)
    assert any(event[0] == "bind_refund" and event[2] is True for event in store.events)


@pytest.mark.parametrize("service_type", [FulfillmentService, FulfillmentRuntimeService])
def test_exact_sitescore_refund_metadata_still_recovers_without_second_refund(service_type):
    service, store, refunds = _unit_service(service_type, _expected_metadata(uuid4()))
    refunds.existing = (
        RefundEvidence(
            "re_exact",
            "pi_paid",
            1000,
            "USD",
            "succeeded",
            _expected_metadata(store.current.order_id),
        ),
    )

    result = service.advance(store.current.order_id)

    assert result.order_state == "refunded"
    assert result.payment_state == "refunded"
    assert not any(call[0] == "create" for call in refunds.calls)
    assert any(event[0] == "bind_refund" and event[2] is False for event in store.events)


def _postgres_runtime(existing_metadata: dict[str, str] | None, *, metadata_mode: str):
    assert DATABASE_URL is not None
    migrate()
    commerce = CommerceStore(DATABASE_URL)
    order_id, _ = paid_order(commerce)
    store = FulfillmentStore(commerce)
    store.prepare_analysis_operation(order_id=order_id, settings=postgres_settings())
    analysis_id = uuid4()
    store.bind_analysis(order_id=order_id, evidence=AnalysisEvidence(analysis_id, "failed"))

    sitescore = FakeSiteScore()
    sitescore.analysis = AnalysisEvidence(analysis_id, "failed")
    refunds = FakeRefunds()
    checkout = commerce.load_order_and_checkout(order_id)[1]
    payment_intent_id = checkout.stripe_payment_intent_id
    assert payment_intent_id is not None
    refunds.pi = PaymentIntentEvidence(
        payment_intent_id,
        1234,
        "USD",
        False,
        {
            "sitescore_order_id": str(order_id),
            "sitescore_product_code": "location_report_v1",
        },
    )

    if metadata_mode == "mutation":
        assert existing_metadata is not None
        metadata = dict(existing_metadata)
    elif metadata_mode == "external":
        metadata = {}
    elif metadata_mode == "exact":
        metadata = _expected_metadata(order_id)
    else:
        raise AssertionError(metadata_mode)

    refunds.existing = (
        RefundEvidence(
            "re_existing_" + uuid4().hex,
            payment_intent_id,
            1234,
            "USD",
            "succeeded",
            metadata,
        ),
    )
    service = FulfillmentRuntimeService(postgres_settings(), store, sitescore, refunds)
    return service, store, refunds, order_id


@pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
@pytest.mark.parametrize("mutation", ["wrong_order", "wrong_operation", "wrong_reason", "partial"])
def test_postgresql_reserved_sitescore_metadata_mismatch_is_durably_attention_required(mutation):
    # Build once to get a real order identity, then replace the provider history with
    # the mutation derived from that exact durable order before advancing.
    service, store, refunds, order_id = _postgres_runtime(
        {"sitescore_order_id": "placeholder"},
        metadata_mode="mutation",
    )
    refunds.existing = (
        RefundEvidence(
            "re_conflicting_" + uuid4().hex,
            refunds.pi.payment_intent_id,
            1234,
            "USD",
            "succeeded",
            _mutated_metadata(order_id, mutation),
        ),
    )

    result = service.advance(order_id)

    assert result.order_state == "attention_required"
    assert result.payment_state == "refund_failed"
    assert result.fulfillment_state == "analysis_failed"
    assert not any(call[0] == "create" for call in refunds.calls)
    with store.session_factory() as session:
        order = session.get(OrderRow, order_id)
        refund = session.get(RefundOperationRow, order_id)
        assert order is not None and refund is not None
        assert order.order_state == "attention_required"
        assert order.payment_state == "refund_failed"
        assert order.fulfillment_state == "analysis_failed"
        assert refund.stripe_refund_id is None
        assert refund.stripe_refund_status is None
        assert refund.failure_code == "conflicting_refund_metadata"


@pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
def test_postgresql_unattributed_external_full_refund_reconciles_without_second_money_effect():
    service, store, refunds, order_id = _postgres_runtime({}, metadata_mode="external")
    existing_id = refunds.existing[0].refund_id

    result = service.advance(order_id)

    assert result.order_state == "refunded"
    assert result.payment_state == "refunded"
    assert not any(call[0] == "create" for call in refunds.calls)
    with store.session_factory() as session:
        order = session.get(OrderRow, order_id)
        refund = session.get(RefundOperationRow, order_id)
        assert order is not None and refund is not None
        assert order.order_state == "refunded"
        assert order.payment_state == "refunded"
        assert refund.stripe_refund_id == existing_id
        assert refund.stripe_refund_status == "succeeded"
        assert refund.failure_code == "provider_already_fully_refunded"


@pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")
def test_postgresql_exact_sitescore_refund_metadata_recovers_without_second_money_effect():
    service, store, refunds, order_id = _postgres_runtime({}, metadata_mode="exact")
    existing_id = refunds.existing[0].refund_id

    result = service.advance(order_id)

    assert result.order_state == "refunded"
    assert result.payment_state == "refunded"
    assert not any(call[0] == "create" for call in refunds.calls)
    with store.session_factory() as session:
        order = session.get(OrderRow, order_id)
        refund = session.get(RefundOperationRow, order_id)
        assert order is not None and refund is not None
        assert order.order_state == "refunded"
        assert order.payment_state == "refunded"
        assert refund.stripe_refund_id == existing_id
        assert refund.stripe_refund_status == "succeeded"
        assert refund.failure_code is None
