"""0009_user_university_affiliation

Revision ID: b75045c68793
Revises: 44a9768a2991
Create Date: 2026-10-07 10:52:23.635280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.models.rbac


# revision identifiers, used by Alembic.
revision: str = 'b75045c68793'
down_revision: Union[str, Sequence[str], None] = '44a9768a2991'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('university_id', app.models.rbac.GUID(), nullable=True))
    op.create_foreign_key(
        'fk_users_university_id', 'users', 'universities', ['university_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_users_university_id', 'users', type_='foreignkey')
    op.drop_column('users', 'university_id')
