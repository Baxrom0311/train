"""0028_account_security

Hisob xavfsizligi (CONTRACT.md §30): `users.email_verified_at`,
`users.password_changed_at`, bir martalik havola tokenlari `account_tokens`.
Mavjud foydalanuvchilar tasdiqlangan deb belgilanadi — ular bu qoidadan
oldin ro'yxatdan o'tgan.

Revision ID: 0028_account_security
Revises: 0027_team_runs
Create Date: 2026-10-13 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0028_account_security"
down_revision: Union[str, Sequence[str], None] = "0027_team_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET email_verified_at = COALESCE(created_at, now())")

    op.create_table(
        "account_tokens",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("purpose IN ('verify_email', 'reset_password')", name="ck_account_tokens_purpose"),
    )
    op.create_index("ix_account_tokens_user_purpose", "account_tokens", ["user_id", "purpose"])


def downgrade() -> None:
    op.drop_index("ix_account_tokens_user_purpose", table_name="account_tokens")
    op.drop_table("account_tokens")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "email_verified_at")
