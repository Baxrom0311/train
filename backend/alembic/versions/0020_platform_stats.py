"""0020_platform_stats

Platforma statistikasi (CONTRACT.md §21): `ai_usage` jadvali va
`view_platform_stats` ruxsati (admin).

Revision ID: 0020_platform_stats
Revises: 0019_submission_checks
Create Date: 2026-10-08 01:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_platform_stats"
down_revision: Union[str, Sequence[str], None] = "0019_submission_checks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_ID = "00000000-0000-0000-0000-000000000111"


def upgrade() -> None:
    op.create_table(
        "ai_usage",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("failures", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("tokens_in", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("tokens_out", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("day", "provider", "model", "purpose"),
    )
    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'view_platform_stats') ON CONFLICT DO NOTHING"),
        {"id": PERMISSION_ID},
    )
    conn.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'admin' AND p.key = 'view_platform_stats' ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'view_platform_stats')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'view_platform_stats'"))
    op.drop_table("ai_usage")
