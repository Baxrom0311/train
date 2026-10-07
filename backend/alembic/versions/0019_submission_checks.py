"""0019_submission_checks

Kod tekshiruvi (CONTRACT.md §19.4): `submissions.code` va `submissions.check_results`.

Revision ID: 0019_submission_checks
Revises: 0018_notifications
Create Date: 2026-10-08 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0019_submission_checks"
down_revision: Union[str, Sequence[str], None] = "0018_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("code", sa.Text(), nullable=True))
    op.add_column("submissions", sa.Column("check_results", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("submissions", "check_results")
    op.drop_column("submissions", "code")
