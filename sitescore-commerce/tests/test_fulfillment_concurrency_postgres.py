from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from conftest import valid_order
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CheckoutSessionRow, CommerceStore, OrderRow
from sitescore_commerce.fulfillment import AnalysisEvidence, FulfillmentBindingRow, FulfillmentStore
from sitescore_commerce.fulfillment_runtime import FulfillmentRuntimeService
from sitescore_commerce.settings import Settings

DATABASE_URL=os.getenv("SITESCORE_COMMERCE_DATABASE_URL")
pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="requires real PostgreSQL")
ROOT=__import__("pathlib").Path(__file__).resolve().parents[1]


def migrate():
    c=Config(str(ROOT/"alembic.ini")); c.set_main_option("script_location",str(ROOT/"alembic")); command.upgrade(c,"head")

def cfg(): return Settings(DATABASE_URL,"sk_test_not-real","price_1234567890","https://app.example/success","https://app.example/cancel","test","secret",False,"2026-07-29.dahlia","https://sitescore.example","service-secret-long","target-v1",10,"automation-key-test-0123456789")
def seed_paid(commerce):
    req=OrderCreateRequest.model_validate(valid_order()); candidate=uuid4(); oid=commerce.get_or_create_order(candidate_order_id=candidate,key_digest=uuid4().hex+uuid4().hex,request=req,catalog_version="v1",price_id="price_1234567890",quantity=1,operation_version=CHECKOUT_OPERATION_VERSION,checkout_success_url=f"https://app.example/success?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",checkout_cancel_url=f"https://app.example/cancel?order_id={candidate}")
    with commerce.session_factory.begin() as session:
        order=session.get(OrderRow,oid); checkout=session.get(CheckoutSessionRow,oid); order.order_state="paid"; order.payment_state="paid"; order.fulfillment_state="not_started"; checkout.stripe_payment_intent_id=f"pi_{oid.hex}"
    return oid


class NoRefunds:
    def retrieve_payment_intent(self,*a,**k): raise AssertionError("refund must not run")
    def list_refunds(self,*a,**k): raise AssertionError("refund must not run")
    def create_refund(self,*a,**k): raise AssertionError("refund must not run")


class IdempotentSiteScore:
    def __init__(self): self.lock=threading.Lock(); self.ids={}; self.operations=[]
    def submit_analysis(self,op):
        with self.lock:
            self.operations.append(op); aid=self.ids.setdefault(op.idempotency_key,uuid4())
        return AnalysisEvidence(aid,"queued")
    def get_analysis(self,*,base_url,analysis_id): return AnalysisEvidence(analysis_id,"queued")
    def resolve_report(self,**kwargs): raise AssertionError("report must not run")
    def get_report(self,**kwargs): raise AssertionError("report must not run")


def test_concurrent_advance_converges_to_one_logical_analysis_binding_and_stable_operation():
    migrate(); commerce=CommerceStore(DATABASE_URL); oid=seed_paid(commerce); gateway=IdempotentSiteScore(); service=FulfillmentRuntimeService(cfg(),FulfillmentStore(commerce),gateway,NoRefunds())
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(lambda _:service.advance(oid),range(16)))
    with commerce.session_factory() as session:
        binding=session.get(FulfillmentBindingRow,oid); order=session.get(OrderRow,oid); assert binding is not None and binding.analysis_id is not None; assert order.fulfillment_state=="analysis_pending"
    assert len({op.idempotency_key for op in gateway.operations})<=1
    assert len({op.request_sha256 for op in gateway.operations})<=1
    assert all(r.order_id==oid for r in results)


def test_provider_io_occurs_after_order_row_lock_transaction_is_released():
    migrate(); commerce=CommerceStore(DATABASE_URL); oid=seed_paid(commerce)
    class ProbeGateway(IdempotentSiteScore):
        def submit_analysis(self,op):
            # NOWAIT on the same order would fail if prepare_analysis_operation kept
            # its transaction/row lock open across provider I/O.
            with commerce.session_factory.begin() as session:
                row=session.execute(select(OrderRow).where(OrderRow.order_id==oid).with_for_update(nowait=True)).scalar_one(); assert row.order_id==oid
            return super().submit_analysis(op)
    service=FulfillmentRuntimeService(cfg(),FulfillmentStore(commerce),ProbeGateway(),NoRefunds()); result=service.advance(oid); assert result.fulfillment_state=="analysis_pending"
