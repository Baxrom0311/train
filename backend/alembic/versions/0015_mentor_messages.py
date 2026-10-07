"""0015_mentor_messages

Mentorning o'zi boshlagan xabarlari: task izohi va dedlayn eslatmasi
(CONTRACT.md §9.13).

Revision ID: 0015_mentor_messages
Revises: 0014_join_university
Create Date: 2026-10-07 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_mentor_messages"
down_revision: Union[str, Sequence[str], None] = "0014_join_university"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("purpose", sa.String(length=16), nullable=True))
    op.add_column("chat_messages", sa.Column("node_id", sa.String(length=64), nullable=True))
    op.add_column("chat_messages", sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "chat_messages_submission_id_fkey", "chat_messages", "submissions",
        ["submission_id"], ["id"], ondelete="CASCADE",
    )
    op.create_unique_constraint("chat_messages_submission_id_key", "chat_messages", ["submission_id"])
    op.create_check_constraint("ck_chat_messages_purpose", "chat_messages", "purpose IN ('review', 'nudge')")


def downgrade() -> None:
    op.drop_constraint("ck_chat_messages_purpose", "chat_messages", type_="check")
    op.drop_constraint("chat_messages_submission_id_key", "chat_messages", type_="unique")
    op.drop_constraint("chat_messages_submission_id_fkey", "chat_messages", type_="foreignkey")
    op.drop_column("chat_messages", "submission_id")
    op.drop_column("chat_messages", "node_id")
    op.drop_column("chat_messages", "purpose")
