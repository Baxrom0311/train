"""0029_error_monitoring

Xatolarni kuzatish (CONTRACT.md §32): `error_groups` jadvali va
`view_errors` ruxsati (admin).

Revision ID: 0029_error_monitoring
Revises: 0028_account_security
Create Date: 2026-10-14 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0029_error_monitoring"
down_revision: Union[str, Sequence[str], None] = "0028_account_security"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
PERMISSION_ID = "00000000-0000-0000-0000-000000000115"


def upgrade() -> None:
    op.create_table(
        "error_groups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("location", sa.String(300), nullable=False, server_default=sa.text("''")),
        sa.Column("detail", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_request_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source IN ('api', 'worker', 'frontend')", name="ck_error_groups_source"),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_error_groups_status"),
    )
    op.create_index("ix_error_groups_status_last_seen", "error_groups", ["status", "last_seen"])
    op.create_index("ix_error_groups_source_first_seen", "error_groups", ["source", "first_seen"])

    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'view_errors') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    conn.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'admin' AND p.key = 'view_errors' ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'view_errors')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'view_errors'"))
    op.drop_index("ix_error_groups_source_first_seen", table_name="error_groups")
    op.drop_index("ix_error_groups_status_last_seen", table_name="error_groups")
    op.drop_table("error_groups")
