from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from test_recovery_postgres import (
    CommerceStore,
    DATABASE_URL,
    FixedN8n,
    evidence,
    make_order,
    recovery,
    reset_db,
    state,
)

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires real PostgreSQL")


class BlockingGateway:
    def __init__(self, value):
        self.value = value
        self.entered = Event()
        self.release = Event()
        self.calls = 0

    def retrieve(self, session_id):
        self.calls += 1
        self.entered.set()
        assert self.release.wait(timeout=20)
        return self.value


def test_two_overlapping_recovery_runs_share_durable_lease_and_create_one_paid_transition_outbox():
    reset_db(); bootstrap = CommerceStore(DATABASE_URL); oid, sid = make_order(bootstrap)
    gateway = BlockingGateway(evidence(oid, sid))
    first_service = recovery(CommerceStore(DATABASE_URL), gateway, FixedN8n())
    second_service = recovery(CommerceStore(DATABASE_URL), gateway, FixedN8n())

    with ThreadPoolExecutor(max_workers=1) as pool:
        first_future = pool.submit(first_service.run_once)
        assert gateway.entered.wait(timeout=20)
        # The first scanner has committed its lease and is outside the database in the
        # Stripe GET. A truly overlapping scanner must observe the lease and claim zero.
        second = second_service.run_once()
        assert second.claimed == 0
        gateway.release.set()
        first = first_future.result(timeout=20)

    assert first.claimed == 1 and first.reconciled == 1
    assert gateway.calls == 1
    order, _, outboxes, receipts, inbox, findings, _ = state(bootstrap, oid)
    assert (order.order_state, order.payment_state) == ("paid", "paid")
    assert len(outboxes) == 1 and len(receipts) == 1
    assert inbox == [] and findings == []
