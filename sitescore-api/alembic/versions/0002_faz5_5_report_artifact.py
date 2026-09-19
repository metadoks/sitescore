"""FAZ 5.5 delivery-ready report artifact schema

Revision ID: 0002_faz5_5
Revises: 0001_faz5_1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_faz5_5"
down_revision: Union[str, Sequence[str], None] = "0001_faz5_1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("report_artifact_version", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("analysis_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("report_schema_version", sa.String(length=64), nullable=False),
        sa.Column("report_projection_version", sa.String(length=64), nullable=False),
        sa.Column("narrative_prompt_version", sa.String(length=64), nullable=False),
        sa.Column("narrative_schema_version", sa.String(length=64), nullable=False),
        sa.Column("narrative_provider", sa.String(length=64), nullable=False),
        sa.Column("narrative_model_id", sa.String(length=200), nullable=True),
        sa.Column("narrative_generation_mode", sa.String(length=32), nullable=True),
        sa.Column("narrative_fallback_version", sa.String(length=64), nullable=True),
        sa.Column("presentation_schema_version", sa.String(length=64), nullable=False),
        sa.Column("presentation_policy_version", sa.String(length=64), nullable=False),
        sa.Column("template_version", sa.String(length=64), nullable=False),
        sa.Column("stylesheet_version", sa.String(length=64), nullable=False),
        sa.Column("chart_version", sa.String(length=64), nullable=False),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("filename", sa.String(length=200), nullable=True),
        sa.Column("byte_length", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('ready','failed')", name="ck_report_state"),
        sa.CheckConstraint(
            "(state = 'ready' AND content_sha256 IS NOT NULL AND char_length(content_sha256) = 64 "
            "AND mime_type = 'application/pdf' AND filename IS NOT NULL AND byte_length > 0 "
            "AND storage_key IS NOT NULL AND failure_code IS NULL AND failure_message IS NULL "
            "AND narrative_generation_mode IS NOT NULL) OR "
            "(state = 'failed' AND content_sha256 IS NULL AND mime_type IS NULL "
            "AND filename IS NULL AND byte_length IS NULL AND storage_key IS NULL "
            "AND failure_code IS NOT NULL)",
            name="ck_report_state_coherence",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.analysis_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("report_id"),
        sa.UniqueConstraint(
            "analysis_id",
            "report_artifact_version",
            name="uq_reports_analysis_artifact_version",
        ),
    )
    op.create_index("ix_reports_analysis", "reports", ["analysis_id", "report_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reports_analysis", table_name="reports")
    op.drop_table("reports")
