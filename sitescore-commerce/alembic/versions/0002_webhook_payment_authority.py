"""Stripe webhook payment authority and durable reconciliation

Revision ID: 0002_webhook_payment_authority
Revises: 0001_commerce_order_checkout
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_webhook_payment_authority"
down_revision = "0001_commerce_order_checkout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_checkout_sessions_binding_pair", "checkout_sessions", schema="commerce", type_="check")
    op.create_check_constraint(
        "ck_checkout_sessions_url_requires_binding",
        "checkout_sessions",
        "checkout_url IS NULL OR stripe_checkout_session_id IS NOT NULL",
        schema="commerce",
    )
    op.add_column("checkout_sessions", sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True), schema="commerce")
    op.add_column("checkout_sessions", sa.Column("stripe_session_status", sa.String(40), nullable=True), schema="commerce")
    op.add_column("checkout_sessions", sa.Column("stripe_payment_status", sa.String(40), nullable=True), schema="commerce")
    op.add_column("checkout_sessions", sa.Column("stripe_livemode", sa.Boolean(), nullable=True), schema="commerce")
    op.add_column("checkout_sessions", sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True), schema="commerce")
    op.add_column("checkout_sessions", sa.Column("last_reconciliation_event_id", sa.String(255), nullable=True), schema="commerce")

    op.create_table(
        "stripe_event_inbox",
        sa.Column("stripe_event_id", sa.String(255), primary_key=True),
        sa.Column("stripe_event_type", sa.String(128), nullable=False),
        sa.Column("stripe_object_id", sa.String(255), nullable=True),
        sa.Column("event_api_version", sa.String(64), nullable=True),
        sa.Column("livemode", sa.Boolean(), nullable=False),
        sa.Column("event_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_body_sha256", sa.String(64), nullable=False),
        sa.Column("processing_state", sa.String(40), nullable=False),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("processing_state IN ('received','processed','ignored','attention_required')", name="ck_stripe_event_inbox_state"),
        schema="commerce",
    )
    op.create_table(
        "outbox_events",
        sa.Column("outbox_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), nullable=False),
        sa.Column("outbox_type", sa.String(80), nullable=False),
        sa.Column("payload_version", sa.String(16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("order_id", "outbox_type", name="uq_outbox_order_type"),
        sa.CheckConstraint("outbox_type = 'order.paid.v1'", name="ck_outbox_type_6_1"),
        schema="commerce",
    )


def downgrade() -> None:
    op.drop_table("outbox_events", schema="commerce")
    op.drop_table("stripe_event_inbox", schema="commerce")
    op.drop_column("checkout_sessions", "last_reconciliation_event_id", schema="commerce")
    op.drop_column("checkout_sessions", "reconciled_at", schema="commerce")
    op.drop_column("checkout_sessions", "stripe_livemode", schema="commerce")
    op.drop_column("checkout_sessions", "stripe_payment_status", schema="commerce")
    op.drop_column("checkout_sessions", "stripe_session_status", schema="commerce")
    op.drop_column("checkout_sessions", "stripe_payment_intent_id", schema="commerce")
    op.drop_constraint("ck_checkout_sessions_url_requires_binding", "checkout_sessions", schema="commerce", type_="check")
    op.create_check_constraint(
        "ck_checkout_sessions_binding_pair",
        "checkout_sessions",
        "(stripe_checkout_session_id IS NULL AND checkout_url IS NULL) OR (stripe_checkout_session_id IS NOT NULL AND checkout_url IS NOT NULL)",
        schema="commerce",
    )
    # commerce schema is intentionally preserved for commerce.alembic_version.
