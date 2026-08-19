"""Paid fulfillment binding and canonical unfulfillable refund authority

Revision ID: 0003_fulfillment_refund
Revises: 0002_webhook_payment_authority
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_fulfillment_refund"
down_revision = "0002_webhook_payment_authority"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fulfillment_bindings",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), primary_key=True),
        sa.Column("sitescore_api_target_id", sa.String(128), nullable=False),
        sa.Column("sitescore_api_base_url", sa.Text(), nullable=False),
        sa.Column("analysis_operation_version", sa.String(64), nullable=False),
        sa.Column("analysis_idempotency_key", sa.String(255), nullable=False),
        sa.Column("analysis_request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("analysis_request_sha256", sa.String(64), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_state", sa.String(40), nullable=True),
        sa.Column("analysis_last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("report_state", sa.String(40), nullable=True),
        sa.Column("report_last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_idempotency_key", name="uq_fulfillment_bindings_analysis_key"),
        sa.UniqueConstraint("analysis_id", name="uq_fulfillment_bindings_analysis_id"),
        sa.UniqueConstraint("report_id", name="uq_fulfillment_bindings_report_id"),
        sa.CheckConstraint(
            "analysis_state IS NULL OR analysis_state IN ('queued','running','completed','not_score_ready','failed','timed_out')",
            name="ck_fulfillment_bindings_analysis_state",
        ),
        sa.CheckConstraint(
            "report_state IS NULL OR report_state IN ('ready','failed')",
            name="ck_fulfillment_bindings_report_state",
        ),
        schema="commerce",
    )
    op.create_table(
        "refund_eligibility",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), primary_key=True),
        sa.Column("eligibility_reason", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(16), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("server_observed_terminal_state", sa.String(40), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sitescore_api_target_id", sa.String(128), nullable=False),
        sa.CheckConstraint(
            "eligibility_reason IN ('analysis_not_score_ready','analysis_failed','analysis_timed_out','report_failed')",
            name="ck_refund_eligibility_reason",
        ),
        sa.CheckConstraint("resource_type IN ('analysis','report')", name="ck_refund_eligibility_resource_type"),
        sa.CheckConstraint(
            "server_observed_terminal_state IN ('not_score_ready','failed','timed_out')",
            name="ck_refund_eligibility_terminal_state",
        ),
        schema="commerce",
    )
    op.create_table(
        "refund_operations",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), primary_key=True),
        sa.Column("operation_version", sa.String(64), nullable=False),
        sa.Column("provider_idempotency_key", sa.String(255), nullable=False),
        sa.Column("eligibility_reason", sa.String(64), nullable=False),
        sa.Column("eligibility_resource_type", sa.String(16), nullable=False),
        sa.Column("eligibility_resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=False),
        sa.Column("original_amount_received", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("stripe_refund_id", sa.String(255), nullable=True),
        sa.Column("stripe_refund_status", sa.String(40), nullable=True),
        sa.Column("stripe_refund_amount", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("provider_idempotency_key", name="uq_refund_operations_provider_key"),
        sa.UniqueConstraint("stripe_refund_id", name="uq_refund_operations_stripe_refund_id"),
        sa.CheckConstraint("operation_version = 'stripe_full_refund_v1'", name="ck_refund_operations_version"),
        sa.CheckConstraint("original_amount_received > 0", name="ck_refund_operations_positive_amount"),
        sa.CheckConstraint("currency = 'USD'", name="ck_refund_operations_currency"),
        sa.CheckConstraint(
            "stripe_refund_status IS NULL OR stripe_refund_status IN ('pending','requires_action','succeeded','failed','canceled')",
            name="ck_refund_operations_status",
        ),
        schema="commerce",
    )


def downgrade() -> None:
    op.drop_table("refund_operations", schema="commerce")
    op.drop_table("refund_eligibility", schema="commerce")
    op.drop_table("fulfillment_bindings", schema="commerce")
    # commerce schema is intentionally preserved for commerce.alembic_version.
