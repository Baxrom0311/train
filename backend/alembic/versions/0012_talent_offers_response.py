"""0012_talent_offers_response

Talent Hunt: taklifga talaba javobi va `receive_offers` ruxsati (CONTRACT.md §10).

Revision ID: 0012_talent_offers_response
Revises: 74949275f108
Create Date: 2026-10-07 13:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_talent_offers_response"
down_revision: Union[str, Sequence[str], None] = "74949275f108"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RECEIVE_OFFERS_ID = "00000000-0000-0000-0000-000000000106"


def upgrade() -> None:
    op.add_column("talent_offers", sa.Column("response", sa.String(20), nullable=True))
    op.add_column("talent_offers", sa.Column("response_note", sa.String(500), nullable=True))
    op.add_column("talent_offers", sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_talent_offers_response", "talent_offers", "response IS NULL OR response IN ('accepted', 'declined')"
    )
    # Bir kompaniya — bir nomzod: javob kutilayotgan taklif bittadan oshmaydi
    op.create_index(
        "uq_talent_offers_open_pair",
        "talent_offers",
        ["company_id", "candidate_user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('sent', 'viewed')"),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text("INSERT INTO permissions (id, key) VALUES (:id, 'receive_offers') ON CONFLICT DO NOTHING"),
        {"id": RECEIVE_OFFERS_ID},
    )
    conn.execute(sa.text(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'student' AND p.key = 'receive_offers' ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE key = 'receive_offers')"
    ))
    conn.execute(sa.text("DELETE FROM permissions WHERE key = 'receive_offers'"))
    op.drop_index("uq_talent_offers_open_pair", table_name="talent_offers")
    op.drop_constraint("ck_talent_offers_response", "talent_offers", type_="check")
    op.drop_column("talent_offers", "responded_at")
    op.drop_column("talent_offers", "response_note")
    op.drop_column("talent_offers", "response")
