"""0026_cv_settings

Talaba CV'si (CONTRACT.md §28): CV'ga talaba o'zi qo'shadigan narsalar
(telefon, shahar, tillar) va yashirilgan Run'lar. Yangi ruxsat yo'q —
`manage_portfolio` (§13).

Revision ID: 0026_cv_settings
Revises: 0025_company_scenarios
Create Date: 2026-10-11 11:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0026_cv_settings"
down_revision: Union[str, Sequence[str], None] = "0025_company_scenarios"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cv_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("city", sa.String(80), nullable=True),
        sa.Column("languages", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("hidden_run_ids", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cv_settings")
