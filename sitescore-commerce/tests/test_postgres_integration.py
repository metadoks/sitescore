from __future__ import annotations
import os, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import pytest, sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sitescore_commerce.checkout import CHECKOUT_OPERATION_VERSION, CheckoutResult
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CheckoutSessionRow, CommerceStore, IdempotencyConflict, OrderRow
from sitescore_commerce.service import OrderService
from sitescore_commerce.settings import Settings
from conftest import valid_order
DATABASE_URL=os.getenv("SITESCORE_COMMERCE_DATABASE_URL"); pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="requires real PostgreSQL"); ROOT=Path(__file__).resolve().parents[1]
def alembic_config():
    c=Config(str(ROOT/"alembic.ini")); c.set_main_option("script_location",str(ROOT/"alembic")); return c
def migrate(): command.upgrade(alembic_config(),"head")
def create_direct(store,key,request,*,price="price_1234567890",success="https://a.example/success",cancel="https://a.example/cancel"):
    candidate=uuid.uuid4()
    return store.get_or_create_order(candidate_order_id=candidate,key_digest=key,request=request,catalog_version="v1",price_id=price,quantity=1,operation_version=CHECKOUT_OPERATION_VERSION,checkout_success_url=f"{success}?order_id={candidate}&session_id={{CHECKOUT_SESSION_ID}}",checkout_cancel_url=f"{cancel}?order_id={candidate}")
def commerce_settings(price,success,cancel): return Settings(DATABASE_URL,"sk_test_not-real",price,success,cancel,"test")
def test_migration_schema_tables_and_constraints():
    migrate(); engine=sa.create_engine(DATABASE_URL); insp=sa.inspect(engine); assert {"orders","order_idempotency","checkout_sessions","stripe_event_inbox","outbox_events","fulfillment_bindings","refund_eligibility","refund_operations","alembic_version"}<=set(insp.get_table_names(schema="commerce")); assert "alembic_version" not in insp.get_table_names(schema="public")
    cols={c["name"] for c in insp.get_columns("checkout_sessions",schema="commerce")}; assert {"operation_version","stripe_price_id","quantity","customer_email","success_url","cancel_url","stripe_payment_intent_id","stripe_session_status","stripe_payment_status","stripe_livemode","reconciled_at","last_reconciliation_event_id"}<=cols
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO commerce.orders (order_id,product_code,catalog_version,customer_email,purchase_intent,canonical_request_hash,order_state,payment_state,fulfillment_state,created_at,updated_at) VALUES (:order_id,'location_report_v1','v1','x@example.com','{}'::jsonb,repeat('a',64),'forged','pending','not_started',now(),now())"),{"order_id":str(uuid.uuid4())})
def test_upgrade_downgrade_base_upgrade_cycle_is_safe():
    cfg=alembic_config(); command.upgrade(cfg,"head"); command.downgrade(cfg,"base"); engine=sa.create_engine(DATABASE_URL); insp=sa.inspect(engine); assert "commerce" in insp.get_schema_names(); assert set(insp.get_table_names(schema="commerce"))=={"alembic_version"}; command.upgrade(cfg,"head"); insp=sa.inspect(engine); assert {"orders","order_idempotency","checkout_sessions","stripe_event_inbox","outbox_events","fulfillment_bindings","refund_eligibility","refund_operations","alembic_version"}<=set(insp.get_table_names(schema="commerce")); assert "alembic_version" not in insp.get_table_names(schema="public")
    with engine.connect() as conn: assert conn.execute(sa.text("SELECT version_num FROM commerce.alembic_version")).scalar_one()=="0003_fulfillment_refund"
def test_concurrent_same_key_creates_one_durable_order():
    migrate(); store=CommerceStore(DATABASE_URL); request=OrderCreateRequest.model_validate(valid_order())
    def create(): return create_direct(store,"a"*64,request)
    with ThreadPoolExecutor(max_workers=8) as pool: ids=list(pool.map(lambda _:create(),range(16)))
    assert len(set(ids))==1
    with store.session_factory() as session: assert session.query(OrderRow).filter(OrderRow.order_id==ids[0]).count()==1; assert session.query(CheckoutSessionRow).filter(CheckoutSessionRow.order_id==ids[0]).count()==1
def test_same_key_same_payload_reuses_order_and_different_payload_conflicts():
    migrate(); store=CommerceStore(DATABASE_URL); first=OrderCreateRequest.model_validate(valid_order("coffee")); same=OrderCreateRequest.model_validate(valid_order("coffee")); different=OrderCreateRequest.model_validate(valid_order("gym")); key="b"*64; oid=create_direct(store,key,first); assert create_direct(store,key,same,price="price_drift",success="https://drift.example/success",cancel="https://drift.example/cancel")==oid
    _,checkout=store.load_order_and_checkout(oid); assert checkout.stripe_price_id=="price_1234567890" and checkout.success_url.startswith("https://a.example/success") and checkout.cancel_url.startswith("https://a.example/cancel")
    with pytest.raises(IdempotencyConflict): create_direct(store,key,different)
def test_durable_checkout_replay_survives_restart_config_drift_and_bind_loss():
    migrate(); request=OrderCreateRequest.model_validate(valid_order()); calls=[]
    class StableProvider:
        def create_checkout(self,*,operation):
            calls.append(operation)
            return CheckoutResult("cs_test_durable_replay","https://checkout.stripe.com/c/pay/cs_test_durable_replay",datetime(2026,8,20,tzinfo=timezone.utc),"payment",str(operation.order_id),{"sitescore_order_id":str(operation.order_id),"sitescore_product_code":operation.product_code.value,"sitescore_catalog_version":operation.catalog_version})
    first_store=CommerceStore(DATABASE_URL)
    def fail_bind(**_): raise RuntimeError("simulated local bind persistence loss")
    first_store.bind_checkout=fail_bind
    with pytest.raises(RuntimeError,match="simulated local bind"):
        OrderService(commerce_settings("price_A","https://a.example/success","https://a.example/cancel"),first_store,StableProvider()).create_order(request=request,idempotency_key="durable-replay-key")
    assert len(calls)==1; original=calls[0]
    restarted_store=CommerceStore(DATABASE_URL); response=OrderService(commerce_settings("price_B","https://b.example/success","https://b.example/cancel"),restarted_store,StableProvider()).create_order(request=request,idempotency_key="durable-replay-key")
    assert len(calls)==2; replay=calls[1]; assert replay==original; assert replay.stripe_price_id=="price_A"; assert replay.success_url.startswith("https://a.example/success"); assert replay.cancel_url.startswith("https://a.example/cancel"); assert replay.provider_idempotency_key==original.provider_idempotency_key
    _,checkout=restarted_store.load_order_and_checkout(response.order_id); assert checkout.stripe_checkout_session_id=="cs_test_durable_replay"; assert checkout.checkout_url=="https://checkout.stripe.com/c/pay/cs_test_durable_replay"; assert checkout.stripe_price_id=="price_A"; assert checkout.success_url==original.success_url; assert checkout.cancel_url==original.cancel_url
