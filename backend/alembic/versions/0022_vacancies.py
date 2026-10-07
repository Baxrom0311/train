"""0022_vacancies

Kompaniya vakansiyalari (CONTRACT.md §23): `vacancies`, `vacancy_applications`,
`talent_offers.vacancy_id` va `manage_vacancies` ruxsati (company_hr).

Revision ID: 0022_vacancies
Revises: 0021_push_subscriptions
Create Date: 2026-10-08 03:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0022_vacancies"
down_revision: Union[str, Sequence[str], None] = "0021_push_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "00000000-0000-0000-0000-000000000112"
UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()


def _check(name: str, column: str, values: tuple[str, ...]) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def upgrade() -> None:
    op.create_table(
        "vacancies",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("sector", sa.String(20), nullable=False),
        sa.Column("employment", sa.String(20), nullable=False),
        sa.Column("work_format", sa.String(20), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("requirements", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("min_score", sa.Integer(), nullable=True),
        sa.Column("scenario_ids", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        _check("ck_vacancies_sector", "sector", ("IT", "Banking", "Marketing", "Data", "HR")),
        _check("ck_vacancies_employment", "employment", ("full_time", "part_time", "internship")),
        _check("ck_vacancies_work_format", "work_format", ("office", "remote", "hybrid")),
        _check("ck_vacancies_status", "status", ("draft", "open", "closed")),
    )
    op.create_index("ix_vacancies_company_status", "vacancies", ["company_id", "status"])

    op.create_table(
        "vacancy_applications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("vacancy_id", UUID, sa.ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vacancy_id", "user_id", name="uq_vacancy_applications_pair"),
        _check("ck_vacancy_applications_status", "status", ("applied", "withdrawn", "rejected", "offered")),
    )
    op.create_index("ix_vacancy_applications_user", "vacancy_applications", ["user_id"])

    op.add_column(
        "talent_offers",
        sa.Column("vacancy_id", UUID, sa.ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'manage_vacancies') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    conn.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'company_hr' AND p.key = 'manage_vacancies' ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'manage_vacancies')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'manage_vacancies'"))
    op.drop_column("talent_offers", "vacancy_id")
    op.drop_index("ix_vacancy_applications_user", table_name="vacancy_applications")
    op.drop_table("vacancy_applications")
    op.drop_index("ix_vacancies_company_status", table_name="vacancies")
    op.drop_table("vacancies")
