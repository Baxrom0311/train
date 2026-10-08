"""0025_company_scenarios

Kompaniya ssenariylari va sinov topshirig'i (CONTRACT.md §26):
`scenarios.owner_company_id`, `application_assessments` va
`manage_company_scenarios` ruxsati (company_hr).

Revision ID: 0025_company_scenarios
Revises: 0024_application_interviews
Create Date: 2026-10-08 15:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0025_company_scenarios"
down_revision: Union[str, Sequence[str], None] = "0024_application_interviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "00000000-0000-0000-0000-000000000114"
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column("owner_company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_scenarios_owner_company_id", "scenarios", ["owner_company_id"])

    op.create_table(
        "application_assessments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("application_id", UUID, sa.ForeignKey("vacancy_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_id", UUID, sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario_version_id", UUID, sa.ForeignKey("scenario_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", UUID, sa.ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("start_by", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('assigned', 'started', 'cancelled')", name="ck_application_assessments_status"),
    )
    op.create_index("ix_application_assessments_application_id", "application_assessments", ["application_id"])
    op.create_index(
        "uq_application_assessments_assigned", "application_assessments", ["application_id"], unique=True,
        postgresql_where=sa.text("status = 'assigned'"),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'manage_company_scenarios') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    conn.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'company_hr' AND p.key = 'manage_company_scenarios' ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'manage_company_scenarios')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'manage_company_scenarios'"))
    op.drop_index("uq_application_assessments_assigned", table_name="application_assessments")
    op.drop_index("ix_application_assessments_application_id", table_name="application_assessments")
    op.drop_table("application_assessments")
    # ustunsiz kompaniya ssenariylari platforma katalogiga chiqib qolmasin
    op.execute("UPDATE scenarios SET is_active = false WHERE owner_company_id IS NOT NULL")
    op.drop_index("ix_scenarios_owner_company_id", table_name="scenarios")
    op.drop_column("scenarios", "owner_company_id")
