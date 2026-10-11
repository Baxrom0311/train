"""0027_team_runs

Jamoaviy Run (CONTRACT.md §29): `run_teams` (lobby), `run_team_members`
(lobby roli va Run'dagi rollar), `runs.team_id`, `chat_messages.author_id`.
Yangi ruxsat yo'q — Run kabi kirgan faol foydalanuvchi.

Revision ID: 0027_team_runs
Revises: 0026_cv_settings
Create Date: 2026-10-11 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0027_team_runs"
down_revision: Union[str, Sequence[str], None] = "0026_cv_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "run_teams",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("scenario_id", UUID, sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_version_id", UUID, sa.ForeignKey("scenario_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("captain_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invite_code", sa.String(8), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('forming', 'started', 'disbanded')", name="ck_run_teams_status"),
    )
    op.create_index("ix_run_teams_scenario_id", "run_teams", ["scenario_id"])

    op.create_table(
        "run_team_members",
        sa.Column("team_id", UUID, sa.ForeignKey("run_teams.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("roles", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_run_team_members_user_id", "run_team_members", ["user_id"])
    op.create_index(
        "uq_run_team_members_role", "run_team_members", ["team_id", "role"], unique=True,
        postgresql_where=sa.text("role IS NOT NULL"),
    )

    op.add_column(
        "runs",
        sa.Column("team_id", UUID, sa.ForeignKey("run_teams.id", ondelete="SET NULL"), nullable=True, unique=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("author_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "author_id")
    op.drop_column("runs", "team_id")
    op.drop_index("uq_run_team_members_role", table_name="run_team_members")
    op.drop_index("ix_run_team_members_user_id", table_name="run_team_members")
    op.drop_table("run_team_members")
    op.drop_index("ix_run_teams_scenario_id", table_name="run_teams")
    op.drop_table("run_teams")
