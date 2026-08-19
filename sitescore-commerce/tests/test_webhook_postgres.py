from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CommerceStore, EventIdentityConflict, OutboxEventRow, OrderRow, StripeEventInboxRow
from sitescore_commerce.settings import STRIPE_API_VERSION, Settings
from sitescore_commerce.webhook import PaymentProviderUnavailable, PaymentWebhookService, StripeCheckoutEvidence, StripeEventEnvelope, StripeLineItemEvidence

DATABASE_URL=os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="requires real PostgreSQL")
ROOT=Path(__file__).resolve().parents[1]

def cfg():
    c=Config(str(ROOT/"alembic.ini")); c.set_main_option("script_location",str(ROOT/"alembic")); return c

def reset_db():
    command.upgrade(cfg(),"head")
    engine=sa.create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for table in ("refund_operations","refund_eligibility","fulfillment_bindings","outbox_events","stripe_event_inbox","checkout_sessions","order_idempotency","orders"):
            conn.execute(sa.text(f"DELETE FROM commerce.{table}"))

def make_order(store, *, bound=True):
    request=OrderCreateRequest.model_validate(valid_order())
    candidate=uuid4()
    oid=store.get_or_create_order(candidate_order_id=candidate,key_digest=uuid4().hex+uuid4().hex,request=request,catalog_version="v1",price_id="price_1234567890",quantity=1,operation_version=CHECKOUT_OPERATION_VERSION,checkout_success_url=f"https://a.example/success?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",checkout_cancel_url=f"https://a.example/cancel?order_id={candidate}")
    if bound: store.bind_checkout(order_id=oid,stripe_session_id="cs_test_pg",checkout_url="https://checkout.stripe.com/c/pay/cs_test_pg",expires_at=None)
    return oid

def settings(): return Settings(DATABASE_URL,"sk_test_not-real","price_1234567890","https://a.example/success","https://a.example/cancel","test","test-signing-secret",False)

def envelope(oid, *, event_id="evt_pg", event_type="checkout.session.completed"):
    return StripeEventEnvelope(event_id,event_type,STRIPE_API_VERSION,False,datetime(2026,8,19,tzinfo=timezone.utc),"cs_test_pg",str(oid))

def evidence(oid, *, status="complete", payment_status="paid", payment_intent_id="pi_pg"):
    return StripeCheckoutEvidence("cs_test_pg","checkout.session","payment",False,str(oid),{"sitescore_order_id":str(oid),"sitescore_product_code":"location_report_v1","sitescore_catalog_version":"v1"},status,payment_status,payment_intent_id,(StripeLineItemEvidence("price_1234567890",1,"USD"),))

class FixedVerifier:
    def __init__(self,event): self.event=event
    def verify(self,raw_body,signature): return self.event
class FixedGateway:
    def __init__(self,value=None,exc=None): self.value=value; self.exc=exc; self.calls=0
    def retrieve(self,session_id):
        self.calls+=1
        if self.exc: raise self.exc
        return self.value

def service(store,ev,evd): return PaymentWebhookService(settings(),store,FixedVerifier(ev),FixedGateway(evd))

def snapshot(store,oid):
    with store.session_factory() as session:
        order=session.get(OrderRow,oid)
        inbox=list(session.query(StripeEventInboxRow).all())
        outbox=list(session.query(OutboxEventRow).all())
        return (order.order_state,order.payment_state,order.fulfillment_state,inbox,outbox)

def test_paid_transition_is_atomic_idempotent_and_one_outbox_across_duplicate_events():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store)
    svc=service(store,envelope(oid),evidence(oid)); svc.handle(raw_body=b"same",signature="sig"); svc.handle(raw_body=b"same",signature="sig")
    svc2=service(store,envelope(oid,event_id="evt_pg_second"),evidence(oid)); svc2.handle(raw_body=b"second",signature="sig")
    order_state,payment_state,fulfillment,inbox,outbox=snapshot(store,oid)
    assert (order_state,payment_state,fulfillment)==("paid","paid","not_started")
    assert len(inbox)==2 and all(row.processing_state=="processed" for row in inbox)
    assert len(outbox)==1 and outbox[0].outbox_type=="order.paid.v1" and outbox[0].published_at is None
    assert outbox[0].payload=={"order_id":str(oid),"event_type":"order.paid.v1","payload_version":1}

def test_same_event_same_semantics_different_raw_bytes_preserves_first_digest():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store); ev=envelope(oid); evd=evidence(oid)
    first=b'{"same":true}'
    second=b'{ "same" : true }'
    service(store,ev,evd).handle(raw_body=first,signature="sig")
    service(store,ev,evd).handle(raw_body=second,signature="sig")
    _,_,_,inbox,outbox=snapshot(store,oid)
    assert len(inbox)==1 and inbox[0].attempt_count==2
    assert inbox[0].raw_body_sha256==hashlib.sha256(first).hexdigest()
    assert inbox[0].processing_state=="processed" and len(outbox)==1

def test_received_retry_with_different_raw_bytes_resumes_and_pays_once():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store); ev=envelope(oid); evd=evidence(oid)
    first=b'{"retry":1}'
    svc=PaymentWebhookService(settings(),store,FixedVerifier(ev),FixedGateway(exc=PaymentProviderUnavailable("timeout")))
    with pytest.raises(PaymentProviderUnavailable): svc.handle(raw_body=first,signature="sig")
    _,_,_,inbox,outbox=snapshot(store,oid)
    assert len(inbox)==1 and inbox[0].processing_state=="received" and outbox==[]
    assert inbox[0].raw_body_sha256==hashlib.sha256(first).hexdigest()
    restarted=CommerceStore(DATABASE_URL)
    PaymentWebhookService(settings(),restarted,FixedVerifier(ev),FixedGateway(evd)).handle(raw_body=b'{ "retry" : 1 }',signature="sig")
    order_state,payment_state,_,inbox,outbox=snapshot(restarted,oid)
    assert (order_state,payment_state)==("paid","paid")
    assert len(inbox)==1 and inbox[0].attempt_count==2 and inbox[0].processing_state=="processed"
    assert len(outbox)==1 and outbox[0].outbox_type=="order.paid.v1"

def test_webhook_first_recovers_provider_success_local_bind_loss_without_second_session():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store,bound=False)
    svc=service(store,envelope(oid),evidence(oid)); svc.handle(raw_body=b"first",signature="sig")
    order,checkout=store.load_order_and_checkout(oid)
    assert checkout.stripe_checkout_session_id=="cs_test_pg" and checkout.checkout_url is None
    assert checkout.stripe_payment_intent_id=="pi_pg" and checkout.stripe_payment_status=="paid"
    assert (order.order_state,order.payment_state)==("paid","paid")
    assert len(snapshot(store,oid)[4])==1

def test_late_expired_event_cannot_downgrade_paid():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store)
    service(store,envelope(oid),evidence(oid)).handle(raw_body=b"paid",signature="sig")
    exp_event=envelope(oid,event_id="evt_expired_late",event_type="checkout.session.expired")
    service(store,exp_event,evidence(oid,status="expired",payment_status="unpaid",payment_intent_id=None)).handle(raw_body=b"late",signature="sig")
    order_state,payment_state,_,inbox,outbox=snapshot(store,oid)
    assert (order_state,payment_state)==("paid","paid") and len(outbox)==1
    assert {r.stripe_event_id:r.processing_state for r in inbox}["evt_expired_late"]=="attention_required"

def test_expired_is_terminal_and_later_paid_truth_goes_attention():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store)
    exp_event=envelope(oid,event_id="evt_expired",event_type="checkout.session.expired")
    service(store,exp_event,evidence(oid,status="expired",payment_status="unpaid",payment_intent_id=None)).handle(raw_body=b"expired",signature="sig")
    service(store,envelope(oid,event_id="evt_paid_late"),evidence(oid)).handle(raw_body=b"paid-late",signature="sig")
    order_state,payment_state,_,inbox,outbox=snapshot(store,oid)
    assert (order_state,payment_state)==("expired","expired") and outbox==[]
    assert {r.stripe_event_id:r.processing_state for r in inbox}["evt_paid_late"]=="attention_required"

def test_response_loss_after_paid_commit_retries_without_duplicate_outbox():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store); ev=envelope(oid); evd=evidence(oid)
    original=store.apply_reconciliation
    def commit_then_lose(**kwargs): original(**kwargs); raise RuntimeError("response lost")
    store.apply_reconciliation=commit_then_lose
    with pytest.raises(RuntimeError,match="response lost"): service(store,ev,evd).handle(raw_body=b"same",signature="sig")
    restarted=CommerceStore(DATABASE_URL); service(restarted,ev,evd).handle(raw_body=b"same",signature="sig")
    assert snapshot(restarted,oid)[0:2]==("paid","paid") and len(snapshot(restarted,oid)[4])==1

def test_duplicate_event_identity_conflict_fails_closed():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store); ev=envelope(oid); evd=evidence(oid)
    service(store,ev,evd).handle(raw_body=b"canonical",signature="sig")
    conflict=StripeEventEnvelope(ev.event_id,"checkout.session.expired",ev.api_version,ev.livemode,ev.created_at,ev.checkout_session_id,ev.candidate_order_id)
    with pytest.raises(EventIdentityConflict): service(store,conflict,evd).handle(raw_body=b"different",signature="sig")
    assert snapshot(store,oid)[0:2]==("paid","paid") and len(snapshot(store,oid)[4])==1

def test_duplicate_event_session_identity_conflict_fails_closed():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store); ev=envelope(oid); evd=evidence(oid)
    service(store,ev,evd).handle(raw_body=b"canonical",signature="sig")
    conflict=StripeEventEnvelope(ev.event_id,ev.event_type,ev.api_version,ev.livemode,ev.created_at,"cs_test_other",ev.candidate_order_id)
    with pytest.raises(EventIdentityConflict): service(store,conflict,evd).handle(raw_body=b"canonical",signature="sig")
    assert snapshot(store,oid)[0:2]==("paid","paid") and len(snapshot(store,oid)[4])==1

def test_concurrent_same_event_converges_to_one_inbox_one_outbox():
    reset_db(); store=CommerceStore(DATABASE_URL); oid=make_order(store); ev=envelope(oid); evd=evidence(oid)
    def deliver(_):
        local=CommerceStore(DATABASE_URL); service(local,ev,evd).handle(raw_body=b"concurrent",signature="sig")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(deliver,range(16)))
    _,_,_,inbox,outbox=snapshot(store,oid)
    assert len(inbox)==1 and inbox[0].processing_state=="processed" and inbox[0].attempt_count>=1
    assert len(outbox)==1
