"""0024_application_interviews

Suhbat bosqichlari (CONTRACT.md §25): `application_interviews` jadvali va
`vacancy_applications.status`ga `interviewing`.

Revision ID: 0024_application_interviews
Revises: 0023_interviews
Create Date: 2026-10-08 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0024_application_interviews"
down_revision: Union[str, Sequence[str], None] = "0023_interviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()
APPLICATION_STATUSES = ("applied", "withdrawn", "rejected", "offered")


def _check(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def _application_status(values: tuple[str, ...]) -> None:
    op.drop_constraint("ck_vacancy_applications_status", "vacancy_applications", type_="check")
    allowed = ", ".join(f"'{v}'" for v in values)
    op.create_check_constraint("ck_vacancy_applications_status", "vacancy_applications", f"status IN ({allowed})")


def upgrade() -> None:
    _application_status(APPLICATION_STATUSES + ("interviewing",))
    op.create_table(
        "application_interviews",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("vacancy_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("slots", JSONB, nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("place", sa.String(300), nullable=False),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decline_reason", sa.String(500), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=True),
        sa.Column("outcome_note", sa.String(1000), nullable=True),
        sa.Column("reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _check("ck_application_interviews_format", "format", ("online", "office")),
        _check("ck_application_interviews_status", "status",
               ("proposed", "confirmed", "declined", "cancelled", "completed")),
        _check("ck_application_interviews_outcome", "outcome", ("passed", "failed", "no_show")),
    )
    op.create_index("ix_application_interviews_application_id", "application_interviews", ["application_id"])
    op.create_index("ix_application_interviews_status_starts", "application_interviews", ["status", "starts_at"])
    op.create_index(
        "uq_application_interviews_active", "application_interviews", ["application_id"], unique=True,
        postgresql_where=sa.text("status IN ('proposed', 'confirmed')"),
    )


def downgrade() -> None:
    op.drop_index("uq_application_interviews_active", table_name="application_interviews")
    op.drop_index("ix_application_interviews_status_starts", table_name="application_interviews")
    op.drop_index("ix_application_interviews_application_id", table_name="application_interviews")
    op.drop_table("application_interviews")
    # suhbat bosqichidagi arizalar oddiy kutayotgan arizaga qaytadi
    op.execute("UPDATE vacancy_applications SET status = 'applied' WHERE status = 'interviewing'")
    _application_status(APPLICATION_STATUSES)
