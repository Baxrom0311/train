"""0014_join_university

Talaba o'z universitetini tanlaydi/o'zgartiradi (CONTRACT.md §12.1).

Revision ID: 0014_join_university
Revises: 0013_view_org_invoices
Create Date: 2026-10-07 16:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_join_university"
down_revision: Union[str, Sequence[str], None] = "0013_view_org_invoices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "00000000-0000-0000-0000-000000000108"
ROLES = ("student",)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'join_university') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    for role in ROLES:
        conn.execute(sa.text(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = :role AND p.key = 'join_university' ON CONFLICT DO NOTHING"
        ), {"role": role})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'join_university')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'join_university'"))
