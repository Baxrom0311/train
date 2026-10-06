"""merge

Revision ID: 0004_merge
Revises: 0002, 0003_billing
Create Date: 2026-10-07 10:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_merge'
down_revision: Union[str, None] = ('0002', '0003_billing')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
