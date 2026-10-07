"""0021_push_subscriptions

Push bildirishnomalar (CONTRACT.md §22.2): `push_subscriptions`,
`notifications.push_status`, `notification_settings.push_enabled`.

Revision ID: 0021_push_subscriptions
Revises: 0020_platform_stats
Create Date: 2026-10-08 02:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0021_push_subscriptions"
down_revision: Union[str, Sequence[str], None] = "0020_platform_stats"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(1000), nullable=False, unique=True),
        sa.Column("p256dh", sa.String(200), nullable=False),
        sa.Column("auth", sa.String(100), nullable=False),
        sa.Column("user_agent", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_push_subscriptions_user", "push_subscriptions", ["user_id"])
    op.add_column("notifications", sa.Column("push_status", sa.String(10), nullable=True))
    # mavjud bildirishnomalar push'ga ketmaydi (yangi ustun yoqilganda eskilari yog'ilmasin)
    op.execute("UPDATE notifications SET push_status = 'skipped'")
    op.create_index(
        "ix_notifications_push_pending", "notifications", ["created_at"],
        postgresql_where=sa.text("push_status IS NULL"),
    )
    op.add_column(
        "notification_settings",
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("notification_settings", "push_enabled")
    op.drop_index("ix_notifications_push_pending", table_name="notifications")
    op.drop_column("notifications", "push_status")
    op.drop_index("ix_push_subscriptions_user", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
