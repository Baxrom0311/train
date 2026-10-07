"""0007_seed_roles_and_permissions

Revision ID: 55e0c8caf68d
Revises: f87d1674bb0c
Create Date: 2026-10-07 10:23:19.154152

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55e0c8caf68d'
down_revision: Union[str, Sequence[str], None] = 'f87d1674bb0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Barqaror (fixed) UUID'lar — idempotent seed uchun, qayta ishga tushirilsa
# ham dublikat yaratmaydi (ON CONFLICT DO NOTHING bilan).
ROLE_IDS = {
    "student": "00000000-0000-0000-0000-000000000001",
    "company_hr": "00000000-0000-0000-0000-000000000002",
    "university_admin": "00000000-0000-0000-0000-000000000003",
    "admin": "00000000-0000-0000-0000-000000000004",
}

PERMISSION_IDS = {
    "approve_companies": "00000000-0000-0000-0000-000000000101",
    "manage_billing": "00000000-0000-0000-0000-000000000102",
    "manage_simulations": "00000000-0000-0000-0000-000000000103",
    "manage_universities": "00000000-0000-0000-0000-000000000104",
    "view_candidates": "00000000-0000-0000-0000-000000000105",
}

# Qaysi rol qaysi ruxsatlarga ega (CONTRACT.md §4 — permission-based RBAC)
ROLE_PERMISSIONS = {
    "admin": ["approve_companies", "manage_billing", "manage_simulations"],
    "company_hr": ["view_candidates"],
    "university_admin": ["manage_universities"],
    "student": [],
}


def upgrade() -> None:
    """Boshlang'ich rollar, ruxsatlar va ularning bog'lanishini seed qiladi."""
    roles = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("key", sa.String),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    conn = op.get_bind()

    for name, rid in ROLE_IDS.items():
        conn.execute(
            sa.text(
                "INSERT INTO roles (id, name) VALUES (:id, :name) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": rid, "name": name},
        )

    for key, pid in PERMISSION_IDS.items():
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, key) VALUES (:id, :key) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": pid, "key": key},
        )

    for role_name, perm_keys in ROLE_PERMISSIONS.items():
        for perm_key in perm_keys:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:rid, :pid) ON CONFLICT DO NOTHING"
                ),
                {"rid": ROLE_IDS[role_name], "pid": PERMISSION_IDS[perm_key]},
            )


def downgrade() -> None:
    """Seed qilingan ma'lumotlarni olib tashlaydi."""
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_permissions"))
    for pid in PERMISSION_IDS.values():
        conn.execute(sa.text("DELETE FROM permissions WHERE id = :id"), {"id": pid})
    for rid in ROLE_IDS.values():
        conn.execute(sa.text("DELETE FROM roles WHERE id = :id"), {"id": rid})
