from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CheckoutSessionRow, CommerceStore, OrderRow
from sitescore_commerce.fulfillment import (
    AnalysisEvidence,
    FulfillmentBindingRow,
    FulfillmentInvariantError,
    FulfillmentStore,
    PaymentIntentEvidence,
    RefundEligibilityRow,
    RefundEvidence,
    RefundOperationRow,
    ReportEvidence,
)
from sitescore_commerce.settings import Settings

DATABASE_URL=os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="requires real PostgreSQL")
ROOT=__import__("pathlib").Path(__file__).resolve().parents[1]


def cfg():
    c=Config(str(ROOT/"alembic.ini")); c.set_main_option("script_location",str(ROOT/"alembic")); return c

def migrate(): command.upgrade(cfg(),"head")

def settings(target="target-v1",base="https://sitescore.example"):
    return Settings(DATABASE_URL,"sk_test_not-real","price_1234567890","https://app.example/success","https://app.example/cancel","test","secret",False,"2026-07-29.dahlia",base,"service-secret-long",target,10,"automation-key-test-0123456789")

def paid_order(store,sector="coffee"):
    request=OrderCreateRequest.model_validate(valid_order(sector)); candidate=uuid4(); oid=store.get_or_create_order(candidate_order_id=candidate,key_digest=uuid4().hex+uuid4().hex,request=request,catalog_version="v1",price_id="price_1234567890",quantity=1,operation_version=CHECKOUT_OPERATION_VERSION,checkout_success_url=f"https://app.example/success?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",checkout_cancel_url=f"https://app.example/cancel?order_id={candidate}")
    with store.session_factory.begin() as session:
        order=session.get(OrderRow,oid); checkout=session.get(CheckoutSessionRow,oid); order.order_state="paid"; order.payment_state="paid"; order.fulfillment_state="not_started"; checkout.stripe_payment_intent_id=f"pi_{oid.hex}"; checkout.stripe_livemode=False
    return oid,request


def test_analysis_snapshot_uses_exact_durable_order_payload_and_survives_config_drift():
    migrate(); commerce=CommerceStore(DATABASE_URL); oid,request=paid_order(commerce,"gym"); store=FulfillmentStore(commerce); first=store.prepare_analysis_operation(order_id=oid,settings=settings("target-a","https://a.example")); second=store.prepare_analysis_operation(order_id=oid,settings=settings("target-b","https://b.example")); assert first==second; assert first.request_json==request.analysis_request.model_dump(mode="json"); assert first.idempotency_key==f"sitescore:analysis:v1:{oid}"; assert first.target_id=="target-a" and first.base_url=="https://a.example"


def test_concurrent_analysis_snapshot_creation_converges_to_one_row_and_one_key():
    migrate(); commerce=CommerceStore(DATABASE_URL); oid,_=paid_order(commerce); store=FulfillmentStore(commerce)
    with ThreadPoolExecutor(max_workers=8) as pool: operations=list(pool.map(lambda _:store.prepare_analysis_operation(order_id=oid,settings=settings()),range(16)))
    assert len({x.idempotency_key for x in operations})==1 and len({x.request_sha256 for x in operations})==1
    with store.session_factory() as session: assert session.query(FulfillmentBindingRow).filter_by(order_id=oid).count()==1


@pytest.mark.parametrize("state,fulfillment",[("queued","analysis_pending"),("running","analysis_running"),("completed","report_pending"),("not_score_ready","not_score_ready"),("failed","analysis_failed"),("timed_out","analysis_timed_out")])
def test_analysis_state_mapping_is_durable(state,fulfillment):
    migrate(); commerce=CommerceStore(DATABASE_URL); oid,_=paid_order(commerce); store=FulfillmentStore(commerce); store.prepare_analysis_operation(order_id=oid,settings=settings()); aid=uuid4(); store.bind_analysis(order_id=oid,evidence=AnalysisEvidence(aid,state));
    with store.session_factory() as session:
        order=session.get(OrderRow,oid); binding=session.get(FulfillmentBindingRow,oid); assert order.order_state=="fulfillment_in_progress" and order.payment_state=="paid" and order.fulfillment_state==fulfillment; assert binding.analysis_id==aid and binding.analysis_state==state and binding.analysis_last_observed_at is not None


def test_analysis_binding_cannot_be_overwritten_or_shared_across_orders():
    migrate(); commerce=CommerceStore(DATABASE_URL); store=FulfillmentStore(commerce); oid1,_=paid_order(commerce); oid2,_=paid_order(commerce); store.prepare_analysis_operation(order_id=oid1,settings=settings()); store.prepare_analysis_operation(order_id=oid2,settings=settings()); aid=uuid4(); store.bind_analysis(order_id=oid1,evidence=AnalysisEvidence(aid,"queued"))
    with pytest.raises(FulfillmentInvariantError): store.bind_analysis(order_id=oid1,evidence=AnalysisEvidence(uuid4(),"queued"))
    with pytest.raises(FulfillmentInvariantError): store.bind_analysis(order_id=oid2,evidence=AnalysisEvidence(aid,"queued"))


@pytest.mark.parametrize("state,fulfillment",[("ready","delivery_pending"),("failed","report_failed")])
def test_report_binding_requires_completed_analysis_and_maps_durably(state,fulfillment):
    migrate(); commerce=CommerceStore(DATABASE_URL); oid,_=paid_order(commerce); store=FulfillmentStore(commerce); store.prepare_analysis_operation(order_id=oid,settings=settings()); aid=uuid4(); store.bind_analysis(order_id=oid,evidence=AnalysisEvidence(aid,"completed")); rid=uuid4(); store.bind_report(order_id=oid,evidence=ReportEvidence(rid,aid,state))
    with store.session_factory() as session:
        order=session.get(OrderRow,oid); binding=session.get(FulfillmentBindingRow,oid); assert order.fulfillment_state==fulfillment; assert binding.report_id==rid and binding.report_state==state and binding.report_last_observed_at is not None


def test_report_cannot_bind_before_completed_or_overwrite_or_share_identity():
    migrate(); commerce=CommerceStore(DATABASE_URL); store=FulfillmentStore(commerce); oid1,_=paid_order(commerce); oid2,_=paid_order(commerce); store.prepare_analysis_operation(order_id=oid1,settings=settings()); store.prepare_analysis_operation(order_id=oid2,settings=settings()); aid1=uuid4(); aid2=uuid4(); rid=uuid4()
    store.bind_analysis(order_id=oid1,evidence=AnalysisEvidence(aid1,"running"))
    with pytest.raises(FulfillmentInvariantError): store.bind_report(order_id=oid1,evidence=ReportEvidence(rid,aid1,"ready"))
    store.bind_analysis(order_id=oid1,evidence=AnalysisEvidence(aid1,"completed")); store.bind_analysis(order_id=oid2,evidence=AnalysisEvidence(aid2,"completed")); store.bind_report(order_id=oid1,evidence=ReportEvidence(rid,aid1,"ready"))
    with pytest.raises(FulfillmentInvariantError): store.bind_report(order_id=oid1,evidence=ReportEvidence(uuid4(),aid1,"ready"))
    with pytest.raises(FulfillmentInvariantError): store.bind_report(order_id=oid2,evidence=ReportEvidence(rid,aid2,"ready"))


@pytest.mark.parametrize("state,reason,terminal",[("not_score_ready","analysis_not_score_ready","not_score_ready"),("failed","analysis_failed","failed"),("timed_out","analysis_timed_out","timed_out")])
def test_analysis_refund_eligibility_snapshot_is_immutable(state,reason,terminal):
    migrate(); commerce=CommerceStore(DATABASE_URL); oid,_=paid_order(commerce); store=FulfillmentStore(commerce); store.prepare_analysis_operation(order_id=oid,settings=settings()); aid=uuid4(); store.bind_analysis(order_id=oid,evidence=AnalysisEvidence(aid,state)); store.persist_refund_eligibility(order_id=oid,reason=reason,resource_type="analysis",resource_id=aid,terminal_state=terminal); store.persist_refund_eligibility(order_id=oid,reason=reason,resource_type="analysis",resource_id=aid,terminal_state=terminal)
    with store.session_factory() as session: row=session.get(RefundEligibilityRow,oid); assert row.eligibility_reason==reason and row.resource_id==aid and row.sitescore_api_target_id=="target-v1"
    with pytest.raises(FulfillmentInvariantError): store.persist_refund_eligibility(order_id=oid,reason="analysis_failed" if reason!="analysis_failed" else "analysis_timed_out",resource_type="analysis",resource_id=aid,terminal_state="failed" if reason!="analysis_failed" else "timed_out")


def test_report_failed_refund_eligibility_is_bound_to_report_resource():
    migrate(); commerce=CommerceStore(DATABASE_URL); oid,_=paid_order(commerce); store=FulfillmentStore(commerce); store.prepare_analysis_operation(order_id=oid,settings=settings()); aid=uuid4(); rid=uuid4(); store.bind_analysis(order_id=oid,evidence=AnalysisEvidence(aid,"completed")); store.bind_report(order_id=oid,evidence=ReportEvidence(rid,aid,"failed")); store.persist_refund_eligibility(order_id=oid,reason="report_failed",resource_type="report",resource_id=rid,terminal_state="failed")
    with store.session_factory() as session: row=session.get(RefundEligibilityRow,oid); assert row.resource_type=="report" and row.resource_id==rid


def prepare_refundable(store,commerce):
    oid,_=paid_order(commerce); store.prepare_analysis_operation(order_id=oid,settings=settings()); aid=uuid4(); store.bind_analysis(order_id=oid,evidence=AnalysisEvidence(aid,"failed")); store.persist_refund_eligibility(order_id=oid,reason="analysis_failed",resource_type="analysis",resource_id=aid,terminal_state="failed"); checkout=commerce.load_order_and_checkout(oid)[1]; pi=PaymentIntentEvidence(checkout.stripe_payment_intent_id,1234,"USD",False,{"sitescore_order_id":str(oid),"sitescore_product_code":"location_report_v1"}); op=store.prepare_refund_operation(order_id=oid,payment_intent=pi); return oid,aid,op


def test_refund_operation_is_one_per_order_with_stable_provider_identity_and_money_snapshot():
    migrate(); commerce=CommerceStore(DATABASE_URL); store=FulfillmentStore(commerce); oid,aid,first=prepare_refundable(store,commerce); second=store.prepare_refund_operation(order_id=oid,payment_intent=PaymentIntentEvidence(first.stripe_payment_intent_id,1234,"USD",False,{})); assert first==second; assert first.provider_idempotency_key==f"sitescore:refund:v1:{oid}" and first.original_amount_received==1234 and first.currency=="USD" and first.eligibility_resource_id==aid
    with store.session_factory() as session: assert session.query(RefundOperationRow).filter_by(order_id=oid).count()==1


@pytest.mark.parametrize("status,order_state,payment_state",[("succeeded","refunded","refunded"),("pending","fulfillment_in_progress","refund_pending"),("requires_action","attention_required","refund_pending"),("failed","attention_required","refund_failed"),("canceled","attention_required","refund_failed")])
def test_refund_status_mapping_is_durable_and_preserves_fulfillment_reason(status,order_state,payment_state):
    migrate(); commerce=CommerceStore(DATABASE_URL); store=FulfillmentStore(commerce); oid,_,op=prepare_refundable(store,commerce); evidence=RefundEvidence("re_"+uuid4().hex,op.stripe_payment_intent_id,op.original_amount_received,"USD",status,op.metadata); store.bind_refund(operation=op,evidence=evidence)
    with store.session_factory() as session:
        order=session.get(OrderRow,oid); row=session.get(RefundOperationRow,oid); assert order.order_state==order_state and order.payment_state==payment_state and order.fulfillment_state=="analysis_failed"; assert row.stripe_refund_status==status and row.stripe_refund_amount==1234


def test_refund_binding_cannot_be_overwritten_with_different_provider_refund():
    migrate(); commerce=CommerceStore(DATABASE_URL); store=FulfillmentStore(commerce); _,_,op=prepare_refundable(store,commerce); first=RefundEvidence("re_first",op.stripe_payment_intent_id,op.original_amount_received,"USD","pending",op.metadata); store.bind_refund(operation=op,evidence=first)
    with pytest.raises(FulfillmentInvariantError): store.bind_refund(operation=op,evidence=RefundEvidence("re_second",op.stripe_payment_intent_id,op.original_amount_received,"USD","succeeded",op.metadata))


def test_postgresql_constraints_reject_invalid_6_2_money_and_state_rows():
    migrate(); engine=sa.create_engine(DATABASE_URL); commerce=CommerceStore(DATABASE_URL); oid,_=paid_order(commerce)
    with pytest.raises(IntegrityError):
        with engine.begin() as conn: conn.execute(sa.text("INSERT INTO commerce.refund_operations (order_id,operation_version,provider_idempotency_key,eligibility_reason,eligibility_resource_type,eligibility_resource_id,stripe_payment_intent_id,original_amount_received,currency,created_at,updated_at) VALUES (:oid,'wrong','key','analysis_failed','analysis',:rid,'pi_x',0,'EUR',now(),now())"),{"oid":str(oid),"rid":str(uuid4())})
