"""Recovery and reconciliation durability

Revision ID: 0005_recovery_reconciliation
Revises: 0004_delivery_email
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_recovery_reconciliation"
down_revision = "0004_delivery_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing 0004 rows predate durable signed-event candidate-order lineage.
    # Keep that provenance distinguishable: legacy rows stay NULL, while all
    # post-0005 inserts receive the verified-event lineage marker from the DB.
    op.add_column(
        "stripe_event_inbox",
        sa.Column("candidate_order_id", sa.String(64), nullable=True),
        schema="commerce",
    )
    op.add_column(
        "stripe_event_inbox",
        sa.Column("candidate_order_lineage_version", sa.String(32), nullable=True),
        schema="commerce",
    )
    op.create_check_constraint(
        "ck_stripe_event_inbox_candidate_lineage_version",
        "stripe_event_inbox",
        "candidate_order_lineage_version IS NULL OR candidate_order_lineage_version = 'verified_event_v1'",
        schema="commerce",
    )

    # A legacy received event can only be resumed when its already-stored Stripe
    # object/session identity correlates to exactly one durable local Checkout
    # binding. checkout_sessions.stripe_checkout_session_id is UNIQUE, therefore
    # count=1 is the only recoverable legacy shape. Orphan/otherwise non-unique
    # rows are quarantined durably and are never converted into synthetic signed
    # candidate-order evidence.
    op.execute(
        sa.text(
            """
            UPDATE commerce.stripe_event_inbox AS inbox
               SET processing_state = 'attention_required',
                   failure_code = 'legacy_event_session_correlation_invalid',
                   processed_at = COALESCE(inbox.processed_at, CURRENT_TIMESTAMP)
             WHERE inbox.processing_state = 'received'
               AND inbox.candidate_order_lineage_version IS NULL
               AND (
                    inbox.stripe_object_id IS NULL
                    OR (
                        SELECT COUNT(*)
                          FROM commerce.checkout_sessions AS checkout
                         WHERE checkout.stripe_checkout_session_id = inbox.stripe_object_id
                    ) <> 1
               )
            """
        )
    )

    # SQLAlchemy 0.6 code intentionally does not map the marker; omitting it from
    # INSERT lets PostgreSQL stamp every new verified Event row while legacy rows
    # retained by the upgrade remain NULL and therefore auditable as legacy.
    op.alter_column(
        "stripe_event_inbox",
        "candidate_order_lineage_version",
        server_default=sa.text("'verified_event_v1'"),
        existing_type=sa.String(32),
        schema="commerce",
    )

    op.create_table(
        "recovery_runs",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed", sa.Integer(), nullable=False),
        sa.Column("reconciled", sa.Integer(), nullable=False),
        sa.Column("published", sa.Integer(), nullable=False),
        sa.Column("replayed", sa.Integer(), nullable=False),
        sa.Column("deferred", sa.Integer(), nullable=False),
        sa.Column("attention", sa.Integer(), nullable=False),
        sa.CheckConstraint("claimed >= 0 AND reconciled >= 0 AND published >= 0 AND replayed >= 0 AND deferred >= 0 AND attention >= 0", name="ck_recovery_runs_nonnegative_counts"),
        schema="commerce",
    )
    op.create_table(
        "recovery_state",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_action", sa.String(64), nullable=True),
        sa.Column("last_outcome", sa.String(64), nullable=True),
        sa.Column("last_error_code", sa.String(80), nullable=True),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_recovery_state_attempt_count"),
        sa.CheckConstraint("consecutive_failures >= 0", name="ck_recovery_state_failure_count"),
        sa.CheckConstraint("(lease_token IS NULL) = (lease_expires_at IS NULL)", name="ck_recovery_state_lease_pair"),
        schema="commerce",
    )
    op.create_index("ix_recovery_state_next_attempt", "recovery_state", ["next_attempt_at", "order_id"], schema="commerce")
    op.create_table(
        "payment_poll_receipts",
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(255), nullable=False),
        sa.Column("observed_session_status", sa.String(40), nullable=False),
        sa.Column("observed_payment_status", sa.String(40), nullable=False),
        sa.Column("observed_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("observed_livemode", sa.Boolean(), nullable=False),
        sa.Column("evidence_sha256", sa.String(64), nullable=False),
        sa.Column("transition_target", sa.String(16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_payment_poll_receipts_order"),
        sa.CheckConstraint("source = 'stripe_checkout_server_poll_v1'", name="ck_payment_poll_receipts_source"),
        sa.CheckConstraint("transition_target IN ('paid','expired')", name="ck_payment_poll_receipts_target"),
        sa.CheckConstraint("evidence_sha256 ~ '^[0-9a-f]{64}$'", name="ck_payment_poll_receipts_digest"),
        schema="commerce",
    )
    op.create_table(
        "outbox_replay_audit",
        sa.Column("replay_attempt_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.recovery_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id", ondelete="CASCADE"), nullable=False),
        sa.Column("outbox_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.outbox_events.outbox_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(32), nullable=False),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.CheckConstraint("result IN ('accepted','uncertain','retryable_rejected','attention')", name="ck_outbox_replay_audit_result"),
        schema="commerce",
    )
    op.create_index("ix_outbox_replay_audit_order_time", "outbox_replay_audit", ["order_id", "attempted_at"], schema="commerce")
    op.create_table(
        "recovery_findings",
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.recovery_runs.run_id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("commerce.orders.order_id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="commerce",
    )


def downgrade() -> None:
    op.drop_table("recovery_findings", schema="commerce")
    op.drop_index("ix_outbox_replay_audit_order_time", table_name="outbox_replay_audit", schema="commerce")
    op.drop_table("outbox_replay_audit", schema="commerce")
    op.drop_table("payment_poll_receipts", schema="commerce")
    op.drop_index("ix_recovery_state_next_attempt", table_name="recovery_state", schema="commerce")
    op.drop_table("recovery_state", schema="commerce")
    op.drop_table("recovery_runs", schema="commerce")
    op.drop_constraint(
        "ck_stripe_event_inbox_candidate_lineage_version",
        "stripe_event_inbox",
        schema="commerce",
        type_="check",
    )
    op.drop_column("stripe_event_inbox", "candidate_order_lineage_version", schema="commerce")
    op.drop_column("stripe_event_inbox", "candidate_order_id", schema="commerce")
    # commerce schema is intentionally preserved for commerce.alembic_version.
