"""case_cups

Revision ID: 0005_case_cups
Revises: 0004_merge
Create Date: 2026-10-07 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_case_cups'
down_revision: Union[str, None] = '0004_merge'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table('case_cups',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('sector', sa.String(), nullable=False),
    sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_by_admin_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['created_by_admin_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('case_cup_submissions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('case_cup_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('ai_score', sa.Float(), nullable=True),
    sa.Column('ai_feedback', sa.Text(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['case_cup_id'], ['case_cups.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('case_cup_submissions')
    op.drop_table('case_cups')
