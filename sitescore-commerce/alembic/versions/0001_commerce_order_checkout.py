"""commerce order and Stripe Checkout foundation

Revision ID: 0001_commerce_order_checkout
Revises:
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_commerce_order_checkout"
down_revision = None
branch_labels = None
depends_on = None

ORDER_STATES = "'pending_payment','paid','fulfillment_in_progress','fulfilled','attention_required','expired','refunded'"
PAYMENT_STATES = "'pending','paid','failed','expired','refund_pending','refunded','refund_failed'"
FULFILLMENT_STATES = "'not_started','analysis_pending','analysis_running','report_pending','delivery_pending','completed','not_score_ready','analysis_failed','analysis_timed_out','report_failed','delivery_failed'"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS commerce")
    op.create_table(
        "orders",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("catalog_version", sa.String(32), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=False),
        sa.Column("purchase_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_request_hash", sa.String(64), nullable=False),
        sa.Column("order_state", sa.String(40), nullable=False),
        sa.Column("payment_state", sa.String(40), nullable=False),
        sa.Column("fulfillment_state", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"order_state IN ({ORDER_STATES})", name="ck_orders_order_state"),
        sa.CheckConstraint(f"payment_state IN ({PAYMENT_STATES})", name="ck_orders_payment_state"),
        sa.CheckConstraint(f"fulfillment_state IN ({FULFILLMENT_STATES})", name="ck_orders_fulfillment_state"),
        schema="commerce",
    )
    op.create_table(
        "order_idempotency",
        sa.Column("key_digest", sa.String(64), primary_key=True),
        sa.Column("canonical_request_hash", sa.String(64), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_order_idempotency_order_id"),
        schema="commerce",
    )
    op.create_table(
        "checkout_sessions",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), primary_key=True),
        sa.Column("stripe_checkout_session_id", sa.String(255), nullable=True),
        sa.Column("provider_idempotency_key", sa.String(255), nullable=False),
        sa.Column("operation_version", sa.String(64), nullable=False),
        sa.Column("catalog_version", sa.String(32), nullable=False),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("stripe_price_id", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=False),
        sa.Column("success_url", sa.Text(), nullable=False),
        sa.Column("cancel_url", sa.Text(), nullable=False),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("checkout_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stripe_checkout_session_id", name="uq_checkout_sessions_stripe_id"),
        sa.UniqueConstraint("provider_idempotency_key", name="uq_checkout_sessions_provider_key"),
        sa.CheckConstraint("quantity = 1", name="ck_checkout_sessions_quantity_v1"),
        sa.CheckConstraint("(stripe_checkout_session_id IS NULL AND checkout_url IS NULL) OR (stripe_checkout_session_id IS NOT NULL AND checkout_url IS NOT NULL)", name="ck_checkout_sessions_binding_pair"),
        schema="commerce",
    )


def downgrade() -> None:
    op.drop_table("checkout_sessions", schema="commerce")
    op.drop_table("order_idempotency", schema="commerce")
    op.drop_table("orders", schema="commerce")
    # Intentionally preserve the commerce schema because Alembic's own
    # version table lives at commerce.alembic_version while the revision
    # transition is being processed. A later upgrade safely reuses it.
