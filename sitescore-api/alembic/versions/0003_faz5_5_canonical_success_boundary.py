"""FAZ 5.5 canonical success / report finalization coordination

Revision ID: 0003_faz5_5
Revises: 0002_faz5_5
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_faz5_5"
down_revision: Union[str, Sequence[str], None] = "0002_faz5_5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("canonical_success_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_canonical_success_before_deadline",
        "analyses",
        "canonical_success_at IS NULL OR canonical_success_at < deadline_at",
    )
    op.create_check_constraint(
        "ck_canonical_success_state",
        "analyses",
        "canonical_success_at IS NULL OR state IN ('running','completed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_canonical_success_state", "analyses", type_="check")
    op.drop_constraint("ck_canonical_success_before_deadline", "analyses", type_="check")
    op.drop_column("analyses", "canonical_success_at")
