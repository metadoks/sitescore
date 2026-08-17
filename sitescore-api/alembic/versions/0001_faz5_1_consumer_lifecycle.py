"""FAZ 5.1 consumer lifecycle schema

Revision ID: 0001_faz5_1
Revises: None
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_faz5_1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consumers",
        sa.Column("consumer_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("consumer_id"),
    )
    op.create_table(
        "service_api_keys",
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("consumer_id", sa.Uuid(), nullable=False),
        sa.Column("secret_digest", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["consumer_id"], ["consumers.consumer_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("record_id"),
        sa.UniqueConstraint("key_id", name="uq_service_api_keys_key_id"),
    )
    op.create_index("ix_service_api_keys_consumer", "service_api_keys", ["consumer_id"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("consumer_id", sa.Uuid(), nullable=False),
        sa.Column("creation_request_id", sa.Uuid(), nullable=False),
        sa.Column("api_version", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("readiness_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "state IN ('queued','running','completed','not_score_ready','failed','timed_out')",
            name="ck_analysis_public_state",
        ),
        sa.CheckConstraint(
            "NOT (state = 'not_score_ready' AND result_body IS NOT NULL)",
            name="ck_not_score_ready_no_scored_result",
        ),
        sa.CheckConstraint(
            "NOT (state IN ('queued','running') AND finished_at IS NOT NULL)",
            name="ck_nonterminal_not_finished",
        ),
        sa.ForeignKeyConstraint(["consumer_id"], ["consumers.consumer_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("analysis_id"),
        sa.UniqueConstraint("consumer_id", "idempotency_key", name="uq_analysis_consumer_idempotency"),
    )
    op.create_index("ix_analysis_consumer_analysis", "analyses", ["consumer_id", "analysis_id"], unique=False)
    op.create_index("ix_analysis_deadline", "analyses", ["state", "deadline_at"], unique=False)

    op.create_table(
        "dispatch_outbox",
        sa.Column("outbox_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("outbox_id"),
        sa.UniqueConstraint("analysis_id", name="uq_dispatch_outbox_analysis"),
    )
    op.create_index("ix_dispatch_outbox_pending", "dispatch_outbox", ["dispatched_at", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dispatch_outbox_pending", table_name="dispatch_outbox")
    op.drop_table("dispatch_outbox")
    op.drop_index("ix_analysis_deadline", table_name="analyses")
    op.drop_index("ix_analysis_consumer_analysis", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_service_api_keys_consumer", table_name="service_api_keys")
    op.drop_table("service_api_keys")
    op.drop_table("consumers")
