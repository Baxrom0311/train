"""0013_view_org_invoices

Tashkilot xodimlari o'z invoice'larini ko'radi (CONTRACT.md §11.3).

Revision ID: 0013_view_org_invoices
Revises: 0012_talent_offers_response
Create Date: 2026-10-07 14:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_view_org_invoices"
down_revision: Union[str, Sequence[str], None] = "0012_talent_offers_response"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "00000000-0000-0000-0000-000000000107"
ROLES = ("company_hr", "university_admin")


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'view_org_invoices') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    for role in ROLES:
        conn.execute(sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = :role AND p.key = 'view_org_invoices' ON CONFLICT DO NOTHING"
        ), {"role": role})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'view_org_invoices')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'view_org_invoices'"))
