from __future__ import annotations
import os, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest, sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sitescore_commerce.contracts import OrderCreateRequest
from sitescore_commerce.db import CheckoutSessionRow, CommerceStore, IdempotencyConflict, OrderRow
from conftest import valid_order
DATABASE_URL=os.getenv("SITESCORE_COMMERCE_DATABASE_URL"); pytestmark=pytest.mark.skipif(not DATABASE_URL,reason="requires real PostgreSQL"); ROOT=Path(__file__).resolve().parents[1]
def migrate():
    c=Config(str(ROOT/"alembic.ini")); c.set_main_option("script_location",str(ROOT/"alembic")); command.upgrade(c,"head")
def test_migration_schema_tables_and_constraints():
    migrate(); engine=sa.create_engine(DATABASE_URL); insp=sa.inspect(engine); assert {"orders","order_idempotency","checkout_sessions","alembic_version"}<=set(insp.get_table_names(schema="commerce")); assert "alembic_version" not in insp.get_table_names(schema="public")
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO commerce.orders (order_id,product_code,catalog_version,customer_email,purchase_intent,canonical_request_hash,order_state,payment_state,fulfillment_state,created_at,updated_at) VALUES (:order_id,'location_report_v1','v1','x@example.com','{}'::jsonb,repeat('a',64),'forged','pending','not_started',now(),now())"),{"order_id":str(uuid.uuid4())})
def test_concurrent_same_key_creates_one_durable_order():
    migrate(); store=CommerceStore(DATABASE_URL); request=OrderCreateRequest.model_validate(valid_order())
    def create(): return store.get_or_create_order(key_digest="a"*64,request=request,catalog_version="v1",price_id="price_1234567890")
    with ThreadPoolExecutor(max_workers=8) as pool: ids=list(pool.map(lambda _:create(),range(16)))
    assert len(set(ids))==1
    with store.session_factory() as session: assert session.query(OrderRow).count()==1; assert session.query(CheckoutSessionRow).count()==1
def test_same_key_same_payload_reuses_order_and_different_payload_conflicts():
    migrate(); store=CommerceStore(DATABASE_URL); first=OrderCreateRequest.model_validate(valid_order("coffee")); same=OrderCreateRequest.model_validate(valid_order("coffee")); different=OrderCreateRequest.model_validate(valid_order("gym")); key="b"*64; oid=store.get_or_create_order(key_digest=key,request=first,catalog_version="v1",price_id="price_1234567890"); assert store.get_or_create_order(key_digest=key,request=same,catalog_version="v1",price_id="price_1234567890")==oid
    with pytest.raises(IdempotencyConflict): store.get_or_create_order(key_digest=key,request=different,catalog_version="v1",price_id="price_1234567890")
