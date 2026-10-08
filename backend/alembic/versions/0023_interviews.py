"""0023_interviews

AI suhbat mashqi (CONTRACT.md §24): `interviews`, `interview_messages` va
`practice_interviews` ruxsati (student).

Revision ID: 0023_interviews
Revises: 0022_vacancies
Create Date: 2026-10-08 05:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0023_interviews"
down_revision: Union[str, Sequence[str], None] = "0022_vacancies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "00000000-0000-0000-0000-000000000113"
UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()


def _check(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vacancy_id", UUID, sa.ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("position", sa.String(120), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("sector", sa.String(20), nullable=False),
        sa.Column("requirements", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("focus", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("lang", sa.String(2), nullable=False),
        sa.Column("plan", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("current", sa.Integer(), nullable=False),
        sa.Column("follow_ups", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("score", sa.Numeric(4, 1), nullable=True),
        sa.Column("competency_scores", JSONB, nullable=True),
        sa.Column("feedback", JSONB, nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("eval_attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        _check("ck_interviews_sector", "sector", ("IT", "Banking", "Marketing", "Data", "HR")),
        _check("ck_interviews_status", "status", ("active", "evaluating", "completed", "failed", "abandoned")),
    )
    op.create_index("ix_interviews_user_created", "interviews", ["user_id", "created_at"])
    op.create_index(
        "uq_interviews_one_active", "interviews", ["user_id"], unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "interview_messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("interview_id", UUID, sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("generated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("interview_id", "seq", name="uq_interview_messages_seq"),
        _check("ck_interview_messages_role", "role", ("interviewer", "candidate")),
        _check("ck_interview_messages_kind", "kind", ("question", "follow_up", "answer", "closing")),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'practice_interviews') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    conn.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'student' AND p.key = 'practice_interviews' ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'practice_interviews')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'practice_interviews'"))
    op.drop_table("interview_messages")
    op.drop_index("uq_interviews_one_active", table_name="interviews")
    op.drop_index("ix_interviews_user_created", table_name="interviews")
    op.drop_table("interviews")
