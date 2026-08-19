from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest

from sitescore_commerce.contracts import FulfillmentState, OrderState, PaymentState
from sitescore_commerce.fulfillment import (
    ANALYSIS_OPERATION_VERSION,
    REFUND_OPERATION_VERSION,
    AnalysisEvidence,
    AnalysisOperation,
    AutomationStatus,
    FulfillmentInvariantError,
    FulfillmentService,
    PaymentIntentEvidence,
    RefundEvidence,
    RefundOperation,
    ReportEvidence,
    SiteScoreHttpGateway,
    SiteScoreProviderUnavailable,
    validate_payment_intent,
    validate_refund_for_operation,
)
from sitescore_commerce.settings import Settings


def settings(**changes):
    values=dict(
        database_url="postgresql+psycopg://unused/test",
        stripe_secret_key="sk_test_not-real",
        stripe_price_location_report_v1="price_1234567890",
        success_url_base="https://app.example/success",
        cancel_url_base="https://app.example/cancel",
        environment="test",
        stripe_webhook_secret="test-signing-secret",
        stripe_expected_livemode=False,
        sitescore_api_base_url="https://sitescore.example",
        sitescore_api_service_key="sitescore-service-key-test",
        sitescore_api_target_id="target-v1",
        sitescore_api_timeout_seconds=10,
        commerce_automation_api_key="automation-key-test-0123456789",
    )
    values.update(changes)
    return Settings(**values)


def operation(order_id=None, *, analysis_id=None, analysis_state=None, report_id=None, report_state=None):
    oid=order_id or uuid4()
    payload={"sector":"coffee","location":{"country_code":"US","street":"1 Main St","city":"Boston","state":"MA"},"business_inputs":{"target_population":10000,"target_rate":0.5,"capture_rate_conservative":0.01,"capture_rate_base":0.02,"capture_rate_optimistic":0.03,"visit_frequency_per_month":3,"average_ticket":8},"costs":{"monthly_rent":5000,"fixed_labor":12000,"fixed_overhead":2500}}
    return AnalysisOperation(oid,"target-v1","https://sitescore.example",ANALYSIS_OPERATION_VERSION,f"sitescore:analysis:v1:{oid}",payload,"a"*64,analysis_id,analysis_state,report_id,report_state)


class FakeStore:
    def __init__(self, status=None, op=None):
        self.current=status or AutomationStatus(uuid4(),"paid","paid","not_started",True,False,"advance")
        self.op=op
        self.events=[]
        self.order=SimpleNamespace(order_id=self.current.order_id,order_state=self.current.order_state,payment_state=self.current.payment_state,fulfillment_state=self.current.fulfillment_state,product_code="location_report_v1")
        self.checkout=SimpleNamespace(stripe_payment_intent_id="pi_paid")
        self.refund_operation=None

    def get_status(self, order_id):
        return AutomationStatus(order_id,self.current.order_state,self.current.payment_state,self.current.fulfillment_state,self.current.retryable,self.current.terminal,self.current.next_action)

    def prepare_analysis_operation(self,*,order_id,settings):
        self.events.append(("prepare_analysis",order_id,settings.sitescore_api_target_id))
        if self.op is None: self.op=operation(order_id)
        self.current=AutomationStatus(order_id,"fulfillment_in_progress","paid","analysis_pending",True,False,"advance")
        return self.op

    def get_binding(self,order_id): return self.op

    def bind_analysis(self,*,order_id,evidence):
        self.events.append(("bind_analysis",evidence))
        self.op=operation(order_id,analysis_id=evidence.analysis_id,analysis_state=evidence.state,report_id=self.op.report_id if self.op else None,report_state=self.op.report_state if self.op else None)
        mapping={"queued":"analysis_pending","running":"analysis_running","completed":"report_pending","not_score_ready":"not_score_ready","failed":"analysis_failed","timed_out":"analysis_timed_out"}
        self.current=AutomationStatus(order_id,"fulfillment_in_progress","paid",mapping[evidence.state],True,False,"refund" if evidence.state in {"not_score_ready","failed","timed_out"} else "advance")

    def bind_report(self,*,order_id,evidence):
        self.events.append(("bind_report",evidence))
        self.op=operation(order_id,analysis_id=evidence.analysis_id,analysis_state="completed",report_id=evidence.report_id,report_state=evidence.state)
        state="delivery_pending" if evidence.state=="ready" else "report_failed"
        self.current=AutomationStatus(order_id,"fulfillment_in_progress","paid",state,evidence.state=="failed",False,"delivery" if evidence.state=="ready" else "refund")

    def persist_refund_eligibility(self,**kwargs): self.events.append(("eligibility",kwargs))
    def load_refund_context(self,order_id): return self.order,self.checkout,SimpleNamespace(),self.refund_operation
    def prepare_refund_operation(self,*,order_id,payment_intent):
        self.events.append(("prepare_refund",payment_intent))
        reason={"not_score_ready":"analysis_not_score_ready","analysis_failed":"analysis_failed","analysis_timed_out":"analysis_timed_out","report_failed":"report_failed"}[self.current.fulfillment_state]
        rtype="report" if reason=="report_failed" else "analysis"
        rid=self.op.report_id if rtype=="report" else self.op.analysis_id
        self.refund_operation=RefundOperation(order_id,REFUND_OPERATION_VERSION,f"sitescore:refund:v1:{order_id}",reason,rtype,rid,"pi_paid",payment_intent.amount_received,"USD")
        return self.refund_operation
    def bind_refund(self,*,operation,evidence,external_full=False):
        self.events.append(("bind_refund",evidence,external_full))
        if evidence.status=="succeeded": self.current=AutomationStatus(operation.order_id,"refunded","refunded",self.current.fulfillment_state,False,True,"none")
        elif evidence.status=="pending": self.current=AutomationStatus(operation.order_id,self.current.order_state,"refund_pending",self.current.fulfillment_state,True,False,"refund")
        elif evidence.status=="requires_action": self.current=AutomationStatus(operation.order_id,"attention_required","refund_pending",self.current.fulfillment_state,False,False,"none")
        else: self.current=AutomationStatus(operation.order_id,"attention_required","refund_failed",self.current.fulfillment_state,False,False,"none")
    def mark_attention(self,*,order_id,code,refund_failure=False):
        self.events.append(("attention",code,refund_failure)); self.current=AutomationStatus(order_id,"attention_required","refund_failed" if refund_failure else self.current.payment_state,self.current.fulfillment_state,False,False,"none")


class FakeSiteScore:
    def __init__(self): self.calls=[]; self.analysis=AnalysisEvidence(uuid4(),"queued"); self.report=ReportEvidence(uuid4(),self.analysis.analysis_id,"ready")
    def submit_analysis(self,op): self.calls.append(("submit",op)); return self.analysis
    def get_analysis(self,*,base_url,analysis_id): self.calls.append(("get_analysis",base_url,analysis_id)); return self.analysis
    def resolve_report(self,*,base_url,analysis_id): self.calls.append(("resolve_report",base_url,analysis_id)); return self.report
    def get_report(self,*,base_url,report_id): self.calls.append(("get_report",base_url,report_id)); return self.report


class FakeRefunds:
    def __init__(self):
        self.calls=[]; self.pi=PaymentIntentEvidence("pi_paid",1000,"USD",False,{"sitescore_order_id":"","sitescore_product_code":"location_report_v1"}); self.existing=(); self.created_status="succeeded"
    def retrieve_payment_intent(self,payment_intent_id): self.calls.append(("pi",payment_intent_id)); return self.pi
    def list_refunds(self,payment_intent_id): self.calls.append(("list",payment_intent_id)); return tuple(self.existing)
    def create_refund(self,op):
        self.calls.append(("create",op)); return RefundEvidence("re_new",op.stripe_payment_intent_id,op.original_amount_received,op.currency,self.created_status,op.metadata)


def make_service(store,sitescore=None,refunds=None):
    ss=sitescore or FakeSiteScore(); rf=refunds or FakeRefunds(); rf.pi=PaymentIntentEvidence("pi_paid",1000,"USD",False,{"sitescore_order_id":str(store.current.order_id),"sitescore_product_code":"location_report_v1"}); return FulfillmentService(settings(),store,ss,rf),ss,rf


@pytest.mark.parametrize("order_state,payment_state,fulfillment_state",[
    ("pending_payment","pending","not_started"),("expired","expired","not_started"),("refunded","refunded","analysis_failed"),("fulfilled","paid","completed"),("attention_required","paid","analysis_failed"),
])
def test_non_paid_or_terminal_orders_never_start_analysis(order_state,payment_state,fulfillment_state):
    oid=uuid4(); store=FakeStore(AutomationStatus(oid,order_state,payment_state,fulfillment_state,False,order_state in {"expired","refunded","fulfilled"},"none")); service,ss,_=make_service(store); service.advance(oid); assert not ss.calls


@pytest.mark.parametrize("state,expected",[("queued","analysis_pending"),("running","analysis_running"),("completed","report_pending"),("not_score_ready","not_score_ready"),("failed","analysis_failed"),("timed_out","analysis_timed_out")])
def test_analysis_authoritative_state_mapping(state,expected):
    oid=uuid4(); store=FakeStore(AutomationStatus(oid,"paid","paid","not_started",True,False,"advance")); service,ss,_=make_service(store); ss.analysis=AnalysisEvidence(uuid4(),state); result=service.advance(oid); assert result.fulfillment_state==expected and result.payment_state=="paid"


def test_analysis_retry_reuses_durable_operation_identity_and_payload():
    oid=uuid4(); op=operation(oid); store=FakeStore(AutomationStatus(oid,"paid","paid","not_started",True,False,"advance"),op); service,ss,_=make_service(store); ss.analysis=AnalysisEvidence(uuid4(),"queued"); service.advance(oid); first=ss.calls[-1][1]; store.current=AutomationStatus(oid,"paid","paid","not_started",True,False,"advance"); service.advance(oid); second=ss.calls[-1][1]; assert first.idempotency_key==second.idempotency_key==f"sitescore:analysis:v1:{oid}" and first.request_json==second.request_json and first.base_url==second.base_url


@pytest.mark.parametrize("state",["ready","failed"])
def test_report_resolution_only_from_completed_analysis_and_maps_state(state):
    oid=uuid4(); aid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="completed"); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","report_pending",True,False,"advance"),op); service,ss,_=make_service(store); ss.report=ReportEvidence(uuid4(),aid,state); result=service.advance(oid); assert result.fulfillment_state==("delivery_pending" if state=="ready" else "report_failed"); assert ss.calls[-1][0]=="resolve_report"


@pytest.mark.parametrize("state,reason,terminal",[("not_score_ready","analysis_not_score_ready","not_score_ready"),("analysis_failed","analysis_failed","failed"),("analysis_timed_out","analysis_timed_out","timed_out"),("report_failed","report_failed","failed")])
def test_refund_requires_fresh_server_side_terminal_reproof(state,reason,terminal):
    oid=uuid4(); aid=uuid4(); rid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="completed" if state=="report_failed" else terminal,report_id=rid if state=="report_failed" else None,report_state="failed" if state=="report_failed" else None); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid",state,True,False,"refund"),op); service,ss,rf=make_service(store)
    if state=="report_failed": ss.report=ReportEvidence(rid,aid,"failed")
    else: ss.analysis=AnalysisEvidence(aid,terminal)
    result=service.advance(oid); assert result.order_state=="refunded"; assert any(e[0]=="eligibility" and e[1]["reason"]==reason for e in store.events); assert rf.calls[0][0]=="pi"


@pytest.mark.parametrize("local_state,fresh_state",[("not_score_ready","running"),("analysis_failed","completed"),("analysis_timed_out","queued"),("report_failed","ready")])
def test_cached_terminal_state_alone_cannot_authorize_refund(local_state,fresh_state):
    oid=uuid4(); aid=uuid4(); rid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="completed" if local_state=="report_failed" else "failed",report_id=rid if local_state=="report_failed" else None,report_state="failed" if local_state=="report_failed" else None); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid",local_state,True,False,"refund"),op); service,ss,rf=make_service(store)
    if local_state=="report_failed": ss.report=ReportEvidence(rid,aid,fresh_state)
    else: ss.analysis=AnalysisEvidence(aid,fresh_state)
    with pytest.raises(FulfillmentInvariantError): service.advance(oid)
    assert not rf.calls and not any(e[0]=="eligibility" for e in store.events)


@pytest.mark.parametrize("field,value",[
    ("payment_intent_id","pi_other"),("amount_received",0),("amount_received",-1),("currency","EUR"),("currency","usd"),("livemode",True),("metadata_order","wrong"),("metadata_product","wrong"),
])
def test_payment_intent_binding_fail_closed(field,value):
    oid=uuid4(); order=SimpleNamespace(order_id=oid,product_code="location_report_v1"); checkout=SimpleNamespace(stripe_payment_intent_id="pi_paid"); metadata={"sitescore_order_id":str(oid),"sitescore_product_code":"location_report_v1"}; kw=dict(payment_intent_id="pi_paid",amount_received=1000,currency="USD",livemode=False,metadata=metadata)
    if field=="metadata_order": metadata["sitescore_order_id"]=value
    elif field=="metadata_product": metadata["sitescore_product_code"]=value
    else: kw[field]=value
    with pytest.raises(FulfillmentInvariantError): validate_payment_intent(evidence=PaymentIntentEvidence(**kw),order=order,checkout=checkout,expected_livemode=False)


def refund_operation():
    oid=uuid4(); return RefundOperation(oid,REFUND_OPERATION_VERSION,f"sitescore:refund:v1:{oid}","analysis_failed","analysis",uuid4(),"pi_paid",1000,"USD")


@pytest.mark.parametrize("mutation",["bad_id","bad_status","pi","amount","currency","meta_order","meta_operation","meta_reason"])
def test_refund_response_binding_fail_closed(mutation):
    op=refund_operation(); values=dict(refund_id="re_good",payment_intent_id="pi_paid",amount=1000,currency="USD",status="succeeded",metadata=op.metadata.copy())
    if mutation=="bad_id": values["refund_id"]="rf_wrong"
    elif mutation=="bad_status": values["status"]="mystery"
    elif mutation=="pi": values["payment_intent_id"]="pi_other"
    elif mutation=="amount": values["amount"]=999
    elif mutation=="currency": values["currency"]="EUR"
    elif mutation=="meta_order": values["metadata"]["sitescore_order_id"]="wrong"
    elif mutation=="meta_operation": values["metadata"]["sitescore_refund_operation"]="wrong"
    else: values["metadata"]["sitescore_refund_reason"]="wrong"
    with pytest.raises(FulfillmentInvariantError): validate_refund_for_operation(RefundEvidence(**values),op,require_metadata=True)


@pytest.mark.parametrize("status,order_state,payment_state",[("succeeded","refunded","refunded"),("pending","fulfillment_in_progress","refund_pending"),("requires_action","attention_required","refund_pending"),("failed","attention_required","refund_failed"),("canceled","attention_required","refund_failed")])
def test_refund_status_mapping_preserves_terminal_fulfillment_reason(status,order_state,payment_state):
    oid=uuid4(); aid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="failed"); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),op); service,ss,rf=make_service(store); ss.analysis=AnalysisEvidence(aid,"failed"); rf.created_status=status; result=service.advance(oid); assert result.order_state==order_state and result.payment_state==payment_state and result.fulfillment_state=="analysis_failed"


def test_matching_existing_sitescore_refund_is_recovered_without_create():
    oid=uuid4(); aid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="failed"); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),op); service,ss,rf=make_service(store); ss.analysis=AnalysisEvidence(aid,"failed"); rop=RefundOperation(oid,REFUND_OPERATION_VERSION,f"sitescore:refund:v1:{oid}","analysis_failed","analysis",aid,"pi_paid",1000,"USD"); rf.existing=(RefundEvidence("re_existing","pi_paid",1000,"USD","succeeded",rop.metadata),); result=service.advance(oid); assert result.order_state=="refunded" and not any(c[0]=="create" for c in rf.calls)


@pytest.mark.parametrize("refunds",[
    (RefundEvidence("re_partial","pi_paid",500,"USD","succeeded",{}),),
    (RefundEvidence("re_a","pi_paid",500,"USD","succeeded",{}),RefundEvidence("re_b","pi_paid",500,"USD","succeeded",{})),
    (RefundEvidence("re_other","pi_other",1000,"USD","succeeded",{}),),
])
def test_partial_or_conflicting_existing_refunds_fail_closed_without_topup(refunds):
    oid=uuid4(); aid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="failed"); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),op); service,ss,rf=make_service(store); ss.analysis=AnalysisEvidence(aid,"failed"); rf.existing=refunds; result=service.advance(oid); assert result.order_state=="attention_required" and not any(c[0]=="create" for c in rf.calls)


def test_one_unattributed_external_full_refund_reconciles_without_second_refund():
    oid=uuid4(); aid=uuid4(); op=operation(oid,analysis_id=aid,analysis_state="failed"); store=FakeStore(AutomationStatus(oid,"fulfillment_in_progress","paid","analysis_failed",True,False,"refund"),op); service,ss,rf=make_service(store); ss.analysis=AnalysisEvidence(aid,"failed"); rf.existing=(RefundEvidence("re_external","pi_paid",1000,"USD","succeeded",{}),); result=service.advance(oid); assert result.order_state=="refunded" and not any(c[0]=="create" for c in rf.calls); assert any(e[0]=="bind_refund" and e[2] is True for e in store.events)


class Response:
    def __init__(self,status_code=200,payload=None): self.status_code=status_code; self._payload=payload
    def json(self):
        if isinstance(self._payload,Exception): raise self._payload
        return self._payload


@pytest.mark.parametrize("status,retryable",[(401,False),(403,False),(404,False),(409,False),(429,True),(500,True),(502,True),(503,True),(504,True)])
def test_sitescore_http_failures_never_become_terminal_business_truth(monkeypatch,status,retryable):
    monkeypatch.setattr(httpx,"request",lambda *a,**k: Response(status,{"error":"secret"})); gateway=SiteScoreHttpGateway(settings())
    with pytest.raises(SiteScoreProviderUnavailable) as exc: gateway.get_analysis(base_url="https://sitescore.example",analysis_id=uuid4())
    assert exc.value.retryable is retryable


@pytest.mark.parametrize("payload",[
    None, [], {"api_version":"v2","analysis_id":str(uuid4()),"state":"failed"},
    {"api_version":"v1","analysis_id":"not-a-uuid","state":"failed"},
    {"api_version":"v1","analysis_id":str(uuid4()),"state":"future_state"},
])
def test_sitescore_malformed_or_unknown_analysis_response_fails_closed(monkeypatch,payload):
    monkeypatch.setattr(httpx,"request",lambda *a,**k: Response(200,payload)); gateway=SiteScoreHttpGateway(settings())
    with pytest.raises(SiteScoreProviderUnavailable): gateway.get_analysis(base_url="https://sitescore.example",analysis_id=uuid4())
