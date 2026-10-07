"""0016_more_sectors

Yangi sohalar: Marketing, Data, HR (CONTRACT.md §9.11). `scenarios.sector`
native bo'lmagan enum — VARCHAR(7) edi ("Banking"), "Marketing" sig'maydi.
Kelajakdagi sohalar uchun 20 belgi.

Revision ID: 0016_more_sectors
Revises: 0015_mentor_messages
Create Date: 2026-10-07 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_more_sectors"
down_revision: Union[str, Sequence[str], None] = "0015_mentor_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("scenarios", "sector", type_=sa.String(length=20), existing_nullable=False)


def downgrade() -> None:
    new = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM scenarios WHERE sector NOT IN ('IT', 'Banking')"
    ))
    if new:
        raise RuntimeError(f"{new} ta ssenariy yangi sohada — downgrade'dan oldin ularni o'chiring")
    op.alter_column("scenarios", "sector", type_=sa.String(length=7), existing_nullable=False)
