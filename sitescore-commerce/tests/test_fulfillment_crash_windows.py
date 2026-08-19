from __future__ import annotations

from uuid import uuid4

import pytest

from sitescore_commerce.fulfillment import AnalysisEvidence, AutomationStatus, RefundEvidence, RefundProviderUnavailable, ReportEvidence, SiteScoreProviderUnavailable
from sitescore_commerce.fulfillment_runtime import FulfillmentRuntimeService
from test_fulfillment_authority import FakeRefunds, FakeSiteScore, FakeStore, operation, settings


def runtime(store,sitescore=None,refunds=None):
    ss=sitescore or FakeSiteScore(); rf=refunds or FakeRefunds(); rf.pi=rf.pi.__class__("pi_paid",1000,"USD",False,{"sitescore_order_id":str(store.current.order_id),"sitescore_product_code":"location_report_v1"}); return FulfillmentRuntimeService(settings(),store,ss,rf),ss,rf


def test_analysis_post_response_loss_retries_same_durable_target_key_and_payload():
    oid=uuid4(); store=FakeStore(AutomationStatus(oid,"paid","paid","not_started",True,False,"advance")); ss=FakeSiteScore(); stable_id=uuid4(); accepted=[]
    def submit(op):
        accepted.append(op)
        if len(accepted)==1: raise SiteScoreProviderUnavailable("response_lost",retryable=True)
        return AnalysisEvidence(stable_id,"queued")
    ss.submit_analysis=submit; service,_,_=runtime(store,ss)
    with pytest.raises(SiteScoreProviderUnavailable): service.advance(oid)
    assert store.current.fulfillment_state=="analysis_pending" and store.op.analysis_id is None
    result=service.advance(oid); assert result.fulfillment_state=="analysis_pending" and store.op.analysis_id==stable_id; assert len(accepted)==2 and accepted[0]==accepted[1]


def test_bound_analysis_pending_retry_polls_instead_of_resubmitting():
    oid=uuid4(); aid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_pending",True,False,"advance"),operation(oid,analysis_id=aid,analysis_state="queued")); ss=FakeSiteScore(); ss.analysis=AnalysisEvidence(aid,"running"); service,_,_=runtime(store,ss); result=service.advance(oid); assert result.fulfillment_state=="analysis_running"; assert [c[0] for c in ss.calls]==["get_analysis"]


def test_report_resolver_response_local_bind_loss_retries_same_canonical_report():
    oid=uuid4(); aid=uuid4(); rid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","report_pending",True,False,"advance"),operation(oid,analysis_id=aid,analysis_state="completed")); ss=FakeSiteScore(); ss.report=ReportEvidence(rid,aid,"ready"); original=store.bind_report; calls=[]
    def flaky_bind(**kwargs):
        calls.append(kwargs["evidence"])
        if len(calls)==1: raise RuntimeError("local report bind lost")
        return original(**kwargs)
    store.bind_report=flaky_bind; service,_,_=runtime(store,ss)
    with pytest.raises(RuntimeError,match="local report bind lost"): service.advance(oid)
    assert store.current.fulfillment_state=="report_pending" and store.op.report_id is None
    result=service.advance(oid); assert result.fulfillment_state=="delivery_pending" and calls[0]==calls[1] and calls[1].report_id==rid; assert [c[0] for c in ss.calls]==["resolve_report","resolve_report"]


def test_refund_create_response_loss_recovers_matching_provider_refund_without_second_create():
    oid=uuid4(); aid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),operation(oid,analysis_id=aid,analysis_state="failed")); ss=FakeSiteScore(); ss.analysis=AnalysisEvidence(aid,"failed"); rf=FakeRefunds(); created=[]
    def create(op):
        evidence=RefundEvidence("re_stable",op.stripe_payment_intent_id,op.original_amount_received,"USD","succeeded",op.metadata); created.append((op,evidence)); rf.existing=(evidence,); raise RefundProviderUnavailable("response lost")
    rf.create_refund=create; service,_,_=runtime(store,ss,rf)
    with pytest.raises(RefundProviderUnavailable): service.advance(oid)
    assert len(created)==1 and store.current.order_state=="fulfillment_in_progress"
    result=service.advance(oid); assert result.order_state=="refunded" and len(created)==1; assert not any(c[0]=="create" for c in rf.calls)


def test_refund_provider_success_local_bind_loss_recovers_same_refund_on_retry():
    oid=uuid4(); aid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),operation(oid,analysis_id=aid,analysis_state="failed")); ss=FakeSiteScore(); ss.analysis=AnalysisEvidence(aid,"failed"); rf=FakeRefunds(); stable={}; original_bind=store.bind_refund; binds=[]
    def create(op):
        evidence=RefundEvidence("re_stable_bind",op.stripe_payment_intent_id,op.original_amount_received,"USD","succeeded",op.metadata); stable["evidence"]=evidence; rf.existing=(evidence,); rf.calls.append(("create",op)); return evidence
    def flaky_bind(**kwargs):
        binds.append(kwargs["evidence"])
        if len(binds)==1: raise RuntimeError("local refund bind lost")
        return original_bind(**kwargs)
    rf.create_refund=create; store.bind_refund=flaky_bind; service,_,_=runtime(store,ss,rf)
    with pytest.raises(RuntimeError,match="local refund bind lost"): service.advance(oid)
    result=service.advance(oid); assert result.order_state=="refunded" and len([c for c in rf.calls if c[0]=="create"])==1 and binds[0]==binds[1]


def test_refund_retry_reuses_same_durable_operation_identity_after_pending_status():
    oid=uuid4(); aid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),operation(oid,analysis_id=aid,analysis_state="failed")); ss=FakeSiteScore(); ss.analysis=AnalysisEvidence(aid,"failed"); rf=FakeRefunds(); rf.created_status="pending"; service,_,_=runtime(store,ss,rf); first=service.advance(oid); assert first.payment_state=="refund_pending"; created=[c[1] for c in rf.calls if c[0]=="create"]; assert len(created)==1
    rf.existing=(RefundEvidence("re_later",created[0].stripe_payment_intent_id,created[0].original_amount_received,"USD","succeeded",created[0].metadata),); second=service.advance(oid); assert second.order_state=="refunded"; assert len([c for c in rf.calls if c[0]=="create"])==1


def test_matching_refund_plus_any_extra_provider_refund_fails_closed():
    oid=uuid4(); aid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),operation(oid,analysis_id=aid,analysis_state="failed")); ss=FakeSiteScore(); ss.analysis=AnalysisEvidence(aid,"failed"); rf=FakeRefunds(); service,_,_=runtime(store,ss,rf)
    # Materialize the operation once to derive exact SiteScore metadata.
    service.advance(oid); created=[c[1] for c in rf.calls if c[0]=="create"]; assert len(created)==1
    store.current=AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund")
    exact=RefundEvidence("re_exact",created[0].stripe_payment_intent_id,1000,"USD","succeeded",created[0].metadata)
    extra=RefundEvidence("re_extra",created[0].stripe_payment_intent_id,1,"USD","succeeded",{})
    rf.existing=(exact,extra); rf.calls=[]; result=service.advance(oid); assert result.order_state=="attention_required" and result.payment_state=="refund_failed"; assert not any(c[0]=="create" for c in rf.calls)


def test_full_refund_with_conflicting_sitescore_metadata_is_not_treated_as_external_full_refund():
    oid=uuid4(); aid=uuid4(); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),operation(oid,analysis_id=aid,analysis_state="failed")); ss=FakeSiteScore(); ss.analysis=AnalysisEvidence(aid,"failed"); rf=FakeRefunds(); service,_,_=runtime(store,ss,rf)
    # The metadata advertises SiteScore ownership but contradicts this order.
    rf.existing=(RefundEvidence("re_conflict","pi_paid",1000,"USD","succeeded",{"sitescore_order_id":"wrong"}),)
    result=service.advance(oid); assert result.order_state=="attention_required" and result.payment_state=="refund_failed"; assert not any(c[0]=="create" for c in rf.calls)
