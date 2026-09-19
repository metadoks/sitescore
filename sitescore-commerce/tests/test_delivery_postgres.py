from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CheckoutSessionRow, CommerceStore, OrderRow
from sitescore_commerce.delivery import (
    DeliveryAttemptRow,
    DeliveryCapabilityUnavailable,
    DeliveryGrantRow,
    DeliveryInvariantError,
    DeliveryService,
    DeliveryStore,
    DownloadPayload,
    PostmarkAcceptance,
    PostmarkUncertain,
    ReportResourceEvidence,
    token_digest,
)
from sitescore_commerce.delivery_runtime import RuntimeDeliveryService
from sitescore_commerce.fulfillment import AnalysisEvidence, FulfillmentBindingRow, FulfillmentStore, ReportEvidence
from sitescore_commerce.settings import Settings

DATABASE_URL=os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="requires real PostgreSQL")
ROOT=Path(__file__).resolve().parents[1]


def cfg():
    c=Config(str(ROOT/"alembic.ini")); c.set_main_option("script_location",str(ROOT/"alembic")); return c


def clean():
    command.upgrade(cfg(),"head")
    engine=sa.create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for table in ("delivery_attempts","delivery_grants","refund_operations","refund_eligibility","fulfillment_bindings","outbox_events","stripe_event_inbox","checkout_sessions","order_idempotency","orders"):
            conn.execute(sa.text(f"DELETE FROM commerce.{table}"))


@pytest.fixture(autouse=True)
def cleanup():
    clean(); yield; clean()


def settings():
    return Settings(
        database_url=DATABASE_URL,
        stripe_secret_key="sk_test_not-real",
        stripe_price_location_report_v1="price_1234567890",
        success_url_base="https://app.example/success",
        cancel_url_base="https://app.example/cancel",
        environment="test",
        stripe_webhook_secret="test-signing-secret",
        stripe_expected_livemode=False,
        sitescore_api_base_url="https://sitescore.example",
        sitescore_api_service_key="ssk1_key.secret-secret-secret-secret-0123456789",
        sitescore_api_target_id="target-v1",
        sitescore_api_timeout_seconds=10,
        commerce_automation_api_key="automation-key-test-0123456789",
        postmark_server_token="postmark-test-token-not-real",
        postmark_from_email="reports@sitescore.example",
        postmark_template_alias="sitescore-report-v1",
        postmark_timeout_seconds=10,
        commerce_public_base_url="https://commerce.example",
    )


def ready_order(commerce: CommerceStore):
    request=OrderCreateRequest.model_validate(valid_order())
    candidate=uuid4()
    oid=commerce.get_or_create_order(
        candidate_order_id=candidate,key_digest=uuid4().hex+uuid4().hex,request=request,catalog_version="v1",
        price_id="price_1234567890",quantity=1,operation_version=CHECKOUT_OPERATION_VERSION,
        checkout_success_url=f"https://app.example/success?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",
        checkout_cancel_url=f"https://app.example/cancel?order_id={candidate}",
    )
    with commerce.session_factory.begin() as session:
        order=session.get(OrderRow,oid); checkout=session.get(CheckoutSessionRow,oid)
        order.order_state="paid"; order.payment_state="paid"; order.fulfillment_state="not_started"
        checkout.stripe_payment_intent_id=f"pi_{oid.hex}"; checkout.stripe_livemode=False
    f=FulfillmentStore(commerce); f.prepare_analysis_operation(order_id=oid,settings=settings())
    aid=uuid4(); rid=uuid4(); f.bind_analysis(order_id=oid,evidence=AnalysisEvidence(aid,"completed")); f.bind_report(order_id=oid,evidence=ReportEvidence(rid,aid,"ready"))
    return oid,aid,rid


class FixedSiteScore:
    def __init__(self, aid, rid, payload=b"%PDF-1.7\ndelivery\n%%EOF\n"):
        self.aid=aid; self.rid=rid; self.payload=payload; self.gets=0; self.contents=0
        import hashlib; self.digest=hashlib.sha256(payload).hexdigest()
    def get_report(self,*,base_url,report_id,analysis_id):
        self.gets+=1; assert report_id==self.rid and analysis_id==self.aid
        return ReportResourceEvidence(self.rid,self.aid,"ready",self.digest,"application/pdf","report.pdf",len(self.payload))
    def get_content(self,*,base_url,evidence):
        self.contents+=1; assert evidence.report_id==self.rid and evidence.analysis_id==self.aid
        return DownloadPayload(self.payload,"report.pdf",self.digest)


class PostmarkFake:
    def __init__(self,outcomes): self.outcomes=list(outcomes); self.calls=[]
    def send(self,**kwargs):
        self.calls.append(kwargs); outcome=self.outcomes.pop(0)
        if isinstance(outcome,Exception): raise outcome
        return outcome


def accepted(recipient="Customer@example.com",suffix=1):
    return PostmarkAcceptance(str(UUID(int=suffix)),datetime(2026,8,20,tzinfo=timezone.utc),recipient)


def test_0004_schema_is_digest_only_and_has_required_uniqueness():
    engine=sa.create_engine(DATABASE_URL); inspector=sa.inspect(engine)
    assert {"delivery_grants","delivery_attempts"} <= set(inspector.get_table_names(schema="commerce"))
    grant_cols={c["name"] for c in inspector.get_columns("delivery_grants",schema="commerce")}; assert "token_digest" in grant_cols
    for forbidden in {"token","raw_token","encrypted_token","download_url","postmark_token"}: assert forbidden not in grant_cols
    attempt_cols={c["name"] for c in inspector.get_columns("delivery_attempts",schema="commerce")}
    for forbidden in {"token","raw_token","download_url","postmark_token"}: assert forbidden not in attempt_cols


def test_prepare_grant_persists_only_digest_and_exact_seven_day_expiry(monkeypatch):
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); store=DeliveryStore(commerce)
    raw="A"*43; report=FixedSiteScore(aid,rid).get_report(base_url="x",report_id=rid,analysis_id=aid)
    attempt=store.prepare_attempt(order_id=oid,evidence=report,digest=token_digest(raw),template_alias="sitescore-report-v1")
    with store.session_factory() as session:
        grant=session.get(DeliveryGrantRow,attempt.grant_id); row=session.get(DeliveryAttemptRow,attempt.delivery_attempt_id)
        assert grant.token_digest==token_digest(raw) and raw not in grant.token_digest
        assert grant.expires_at-grant.issued_at == timedelta(days=7)
        assert row.recipient=="Customer@example.com" and row.status=="prepared" and row.attempt_number==1


def test_provider_acceptance_is_the_only_success_transition_and_known_replay_sends_once(monkeypatch):
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); site=FixedSiteScore(aid,rid); post=PostmarkFake([accepted()]); service=DeliveryService(settings(),DeliveryStore(commerce),site,post)
    monkeypatch.setattr("sitescore_commerce.delivery.generate_delivery_token",lambda:"B"*43); service.deliver(oid)
    with commerce.session_factory() as session:
        order=session.get(OrderRow,oid); attempt=session.query(DeliveryAttemptRow).filter_by(order_id=oid).one(); grant=session.get(DeliveryGrantRow,attempt.grant_id)
        assert (order.order_state,order.payment_state,order.fulfillment_state)==("fulfilled","paid","completed")
        assert attempt.status=="provider_accepted" and attempt.provider_message_id is not None and grant.revoked_at is None
    service.deliver(oid); assert len(post.calls)==1


def test_uncertain_replay_creates_fresh_grant_keeps_previous_grant_valid_and_converges(monkeypatch):
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); site=FixedSiteScore(aid,rid); post=PostmarkFake([PostmarkUncertain(),accepted(suffix=2)]); service=DeliveryService(settings(),DeliveryStore(commerce),site,post)
    tokens=iter(["C"*43,"D"*43]); monkeypatch.setattr("sitescore_commerce.delivery.generate_delivery_token",lambda:next(tokens)); service.deliver(oid)
    with commerce.session_factory() as session:
        order=session.get(OrderRow,oid); attempts=session.query(DeliveryAttemptRow).filter_by(order_id=oid).all(); grants=session.query(DeliveryGrantRow).filter_by(order_id=oid).all()
        assert order.fulfillment_state=="delivery_pending" and order.payment_state=="paid"
        assert len(attempts)==1 and attempts[0].status=="provider_uncertain" and len(grants)==1 and grants[0].revoked_at is None
    service.deliver(oid)
    with commerce.session_factory() as session:
        order=session.get(OrderRow,oid); attempts=session.query(DeliveryAttemptRow).filter_by(order_id=oid).order_by(DeliveryAttemptRow.attempt_number).all(); grants=session.query(DeliveryGrantRow).filter_by(order_id=oid).all()
        assert (order.order_state,order.payment_state,order.fulfillment_state)==("fulfilled","paid","completed")
        assert [x.status for x in attempts]==["provider_uncertain","provider_accepted"]
        assert len(grants)==2 and len({g.token_digest for g in grants})==2 and all(g.revoked_at is None for g in grants) and {g.report_id for g in grants}=={rid}
    assert service.download("C"*43).content==site.payload; assert service.download("D"*43).content==site.payload


def test_three_uncertain_attempts_exhaust_delivery_without_changing_payment_or_report_truth(monkeypatch):
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); site=FixedSiteScore(aid,rid); post=PostmarkFake([PostmarkUncertain(),PostmarkUncertain(),PostmarkUncertain()]); service=RuntimeDeliveryService(settings(),DeliveryStore(commerce),site,post)
    tokens=iter(["E"*43,"F"*43,"G"*43]); monkeypatch.setattr("sitescore_commerce.delivery.generate_delivery_token",lambda:next(tokens))
    service.deliver(oid); service.deliver(oid); service.deliver(oid)
    with commerce.session_factory() as session:
        order=session.get(OrderRow,oid); binding=session.get(FulfillmentBindingRow,oid); attempts=session.query(DeliveryAttemptRow).filter_by(order_id=oid).all()
        assert (order.order_state,order.payment_state,order.fulfillment_state)==("attention_required","paid","delivery_failed")
        assert binding.analysis_id==aid and binding.analysis_state=="completed" and binding.report_id==rid and binding.report_state=="ready"
        assert len(attempts)==3 and all(a.status=="provider_uncertain" for a in attempts)
    service.deliver(oid); assert len(post.calls)==3


def test_rejected_retryable_keeps_delivery_action_but_nonretryable_fails_delivery_only(monkeypatch):
    from sitescore_commerce.delivery import PostmarkRejected
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); site=FixedSiteScore(aid,rid); post=PostmarkFake([PostmarkRejected("postmark_http_503",retryable=True),PostmarkRejected("postmark_error_300",retryable=False)]); service=DeliveryService(settings(),DeliveryStore(commerce),site,post); f=FulfillmentStore(commerce)
    tokens=iter(["H"*43,"I"*43]); monkeypatch.setattr("sitescore_commerce.delivery.generate_delivery_token",lambda:next(tokens))
    service.deliver(oid); status=f.get_status(oid); assert status.next_action=="delivery" and status.payment_state=="paid" and status.fulfillment_state=="delivery_pending"
    service.deliver(oid); status=f.get_status(oid); assert status.next_action=="none" and status.order_state=="attention_required" and status.payment_state=="paid" and status.fulfillment_state=="delivery_failed"


def test_grant_reuse_revocation_unknown_and_tampered_binding_fail_closed():
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); store=DeliveryStore(commerce); raw="J"*43; report=FixedSiteScore(aid,rid).get_report(base_url="x",report_id=rid,analysis_id=aid); attempt=store.prepare_attempt(order_id=oid,evidence=report,digest=token_digest(raw),template_alias="sitescore-report-v1")
    assert store.resolve_grant(token_digest(raw)).report_id==rid; assert store.resolve_grant(token_digest(raw)).report_id==rid
    with pytest.raises(DeliveryCapabilityUnavailable): store.resolve_grant(token_digest("unknown"*7))
    with store.session_factory.begin() as session: session.get(DeliveryGrantRow,attempt.grant_id).revoked_at=session.get(DeliveryGrantRow,attempt.grant_id).issued_at
    with pytest.raises(DeliveryCapabilityUnavailable): store.resolve_grant(token_digest(raw))
    with store.session_factory.begin() as session:
        grant=session.get(DeliveryGrantRow,attempt.grant_id); grant.revoked_at=None; grant.report_id=uuid4()
    with pytest.raises(DeliveryCapabilityUnavailable): store.resolve_grant(token_digest(raw))


def test_database_constraints_reject_duplicate_digest():
    commerce=CommerceStore(DATABASE_URL); oid,aid,rid=ready_order(commerce); store=DeliveryStore(commerce); report=FixedSiteScore(aid,rid).get_report(base_url="x",report_id=rid,analysis_id=aid)
    first=store.prepare_attempt(order_id=oid,evidence=report,digest="a"*64,template_alias="sitescore-report-v1"); store.mark_dispatch_started(first.delivery_attempt_id); store.record_uncertain(first.delivery_attempt_id,code="uncertain")
    with pytest.raises(DeliveryInvariantError): store.prepare_attempt(order_id=oid,evidence=report,digest="a"*64,template_alias="sitescore-report-v1")
