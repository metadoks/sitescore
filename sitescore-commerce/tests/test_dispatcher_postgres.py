from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from sitescore_commerce.contracts import FulfillmentState, OrderState, PaymentState
from sitescore_commerce.db import OutboxEventRow, OrderRow
from sitescore_commerce.dispatcher import OutboxDispatchStore

DATABASE_URL = os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")


def insert_paid_event(store: OutboxDispatchStore, *, year: int):
    order_id = uuid4()
    outbox_id = uuid4()
    occurred = datetime(year, 1, 1, tzinfo=timezone.utc)
    with store.session_factory.begin() as session:
        session.add(
            OrderRow(
                order_id=order_id,
                product_code="location_report_v1",
                catalog_version="v1",
                customer_email="dispatcher@example.test",
                purchase_intent={},
                canonical_request_hash="d" * 64,
                order_state=OrderState.PAID.value,
                payment_state=PaymentState.PAID.value,
                fulfillment_state=FulfillmentState.NOT_STARTED.value,
                created_at=occurred,
                updated_at=occurred,
            )
        )
        session.flush()
        session.add(
            OutboxEventRow(
                outbox_id=outbox_id,
                order_id=order_id,
                outbox_type="order.paid.v1",
                payload_version="1",
                payload={
                    "order_id": str(order_id),
                    "event_type": "order.paid.v1",
                    "payload_version": 1,
                    "ignored_extra": "must-never-be-dispatched",
                },
                created_at=occurred,
                published_at=None,
            )
        )
    return order_id, outbox_id, occurred


def cleanup(store: OutboxDispatchStore, order_id, outbox_id):
    with store.session_factory.begin() as session:
        session.execute(delete(OutboxEventRow).where(OutboxEventRow.outbox_id == outbox_id))
        session.execute(delete(OrderRow).where(OrderRow.order_id == order_id))


def test_postgres_load_snapshot_ignores_payload_body_and_marks_published():
    store = OutboxDispatchStore(DATABASE_URL)
    order_id, outbox_id, occurred = insert_paid_event(store, year=1990)
    try:
        item = store.load_next_unpublished()
        assert item is not None
        assert item.event_id == outbox_id
        assert item.order_id == order_id
        assert item.occurred_at == occurred
        assert set(item.payload()) == {"event_id", "event_type", "order_id", "occurred_at"}
        assert "ignored_extra" not in item.payload()

        store.mark_published(outbox_id)
        with store.session_factory() as session:
            row = session.execute(
                select(OutboxEventRow).where(OutboxEventRow.outbox_id == outbox_id)
            ).scalar_one()
            assert row.published_at is not None
    finally:
        cleanup(store, order_id, outbox_id)


def test_two_dispatchers_can_race_without_minting_another_event_identity():
    first = OutboxDispatchStore(DATABASE_URL)
    second = OutboxDispatchStore(DATABASE_URL)
    order_id, outbox_id, _ = insert_paid_event(first, year=1989)
    try:
        a = first.load_next_unpublished()
        b = second.load_next_unpublished()
        assert a is not None and b is not None
        assert a.event_id == b.event_id == outbox_id
        assert a.order_id == b.order_id == order_id

        first.mark_published(outbox_id)
        second.mark_published(outbox_id)

        with first.session_factory() as session:
            rows = session.execute(
                select(OutboxEventRow).where(
                    OutboxEventRow.order_id == order_id,
                    OutboxEventRow.outbox_type == "order.paid.v1",
                )
            ).scalars().all()
            assert len(rows) == 1
            assert rows[0].outbox_id == outbox_id
            assert rows[0].published_at is not None
    finally:
        cleanup(first, order_id, outbox_id)
