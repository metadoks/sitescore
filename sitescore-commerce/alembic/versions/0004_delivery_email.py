"""Delivery capability grants and transactional email evidence

Revision ID: 0004_delivery_email
Revises: 0003_fulfillment_refund
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_delivery_email"
down_revision = "0003_fulfillment_refund"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "delivery_grants",
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_digest", name="uq_delivery_grants_token_digest"),
        sa.CheckConstraint("token_digest ~ '^[0-9a-f]{64}$'", name="ck_delivery_grants_digest_shape"),
        sa.CheckConstraint("expires_at > issued_at", name="ck_delivery_grants_expiry_after_issue"),
        sa.CheckConstraint("revoked_at IS NULL OR revoked_at >= issued_at", name="ck_delivery_grants_revocation_time"),
        schema="commerce",
    )
    op.create_table(
        "delivery_attempts",
        sa.Column("delivery_attempt_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id"), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.delivery_grants.grant_id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("template_alias", sa.String(100), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("attempt_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("provider_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", "attempt_number", name="uq_delivery_attempts_order_number"),
        sa.UniqueConstraint("provider_message_id", name="uq_delivery_attempts_provider_message_id"),
        sa.CheckConstraint("provider = 'postmark'", name="ck_delivery_attempts_provider"),
        sa.CheckConstraint("attempt_number > 0", name="ck_delivery_attempts_positive_number"),
        sa.CheckConstraint(
            "status IN ('prepared','dispatch_started','provider_accepted','provider_rejected','provider_uncertain')",
            name="ck_delivery_attempts_status",
        ),
        schema="commerce",
    )


def downgrade() -> None:
    op.drop_table("delivery_attempts", schema="commerce")
    op.drop_table("delivery_grants", schema="commerce")
    # commerce schema is intentionally preserved for commerce.alembic_version.
