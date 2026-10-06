"""0001_initial_production_schema

Revision ID: 15dfd582b15c
Revises: 
Create Date: 2026-10-06 21:28:54.691564

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15dfd582b15c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Universities
    op.create_table(
        'universities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('official_code', sa.String(length=50), nullable=True),
        sa.Column('total_students', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('official_code')
    )
    op.create_index(op.f('ix_universities_id'), 'universities', ['id'], unique=False)

    # 2. Companies
    op.create_table(
        'companies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_companies_id'), 'companies', ['id'], unique=False)

    # 3. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('university', sa.String(length=255), nullable=True),
        sa.Column('university_id', sa.String(length=36), nullable=True),
        sa.Column('company_id', sa.String(length=36), nullable=True),
        sa.Column('is_vip', sa.Boolean(), nullable=True),
        sa.Column('vip_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('mastery_level', sa.Integer(), nullable=True),
        sa.Column('elo_rating', sa.Integer(), nullable=True),
        sa.Column('xp_points', sa.Integer(), nullable=True),
        sa.Column('adaptive_skill_profile', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 4. Simulations
    op.create_table(
        'simulations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company_id', sa.String(length=36), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('difficulty', sa.String(length=50), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('learning_outcomes', sa.JSON(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('is_case_cup', sa.Boolean(), nullable=True),
        sa.Column('prize_pool', sa.String(length=255), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulations_id'), 'simulations', ['id'], unique=False)
    op.create_index(op.f('ix_simulations_slug'), 'simulations', ['slug'], unique=True)

    # 5. Simulation Tasks
    op.create_table(
        'simulation_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('briefing_text', sa.Text(), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('resource_files', sa.JSON(), nullable=True),
        sa.Column('template_data', sa.Text(), nullable=True),
        sa.Column('rubric_criteria', sa.JSON(), nullable=True),
        sa.Column('model_answer', sa.Text(), nullable=True),
        sa.Column('mentor_persona', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulation_tasks_id'), 'simulation_tasks', ['id'], unique=False)

    # 6. Dynamic Challenges
    op.create_table(
        'dynamic_challenges',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('level', sa.Integer(), nullable=True),
        sa.Column('challenge_type', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('difficulty_label', sa.String(length=50), nullable=True),
        sa.Column('briefing', sa.Text(), nullable=False),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('synthetic_dataset', sa.JSON(), nullable=True),
        sa.Column('starter_code', sa.Text(), nullable=True),
        sa.Column('rubric_criteria', sa.JSON(), nullable=True),
        sa.Column('model_answer', sa.Text(), nullable=True),
        sa.Column('mentor_persona', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dynamic_challenges_id'), 'dynamic_challenges', ['id'], unique=False)

    # 7. Submissions
    op.create_table(
        'submissions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=True),
        sa.Column('dynamic_challenge_id', sa.String(length=36), nullable=True),
        sa.Column('submitted_text', sa.Text(), nullable=True),
        sa.Column('attachment_path', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('elo_change', sa.Integer(), nullable=True),
        sa.Column('xp_earned', sa.Integer(), nullable=True),
        sa.Column('ai_feedback', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dynamic_challenge_id'], ['dynamic_challenges.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['simulation_tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_submissions_id'), 'submissions', ['id'], unique=False)

    # 8. Certificates
    op.create_table(
        'certificates',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('cert_uuid', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('average_score', sa.Float(), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('hmac_signature', sa.String(length=128), nullable=False),
        sa.Column('qr_code_url', sa.String(length=500), nullable=True),
        sa.Column('public_verify_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_certificates_cert_uuid'), 'certificates', ['cert_uuid'], unique=True)
    op.create_index(op.f('ix_certificates_id'), 'certificates', ['id'], unique=False)

    # 9. Case Cup Leaderboard
    op.create_table(
        'case_cup_leaderboard',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_case_cup_leaderboard_id'), 'case_cup_leaderboard', ['id'], unique=False)

    # 10. Talent Offers
    op.create_table(
        'talent_offers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('company_id', sa.String(length=36), nullable=False),
        sa.Column('candidate_id', sa.String(length=36), nullable=False),
        sa.Column('simulation_id', sa.String(length=36), nullable=True),
        sa.Column('position_title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_talent_offers_id'), 'talent_offers', ['id'], unique=False)

    # 11. Transactions
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('plan_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_talent_offers_id'), table_name='talent_offers')
    op.drop_table('talent_offers')
    op.drop_index(op.f('ix_case_cup_leaderboard_id'), table_name='case_cup_leaderboard')
    op.drop_table('case_cup_leaderboard')
    op.drop_index(op.f('ix_certificates_id'), table_name='certificates')
    op.drop_index(op.f('ix_certificates_cert_uuid'), table_name='certificates')
    op.drop_table('certificates')
    op.drop_index(op.f('ix_submissions_id'), table_name='submissions')
    op.drop_table('submissions')
    op.drop_index(op.f('ix_dynamic_challenges_id'), table_name='dynamic_challenges')
    op.drop_table('dynamic_challenges')
    op.drop_index(op.f('ix_simulation_tasks_id'), table_name='simulation_tasks')
    op.drop_table('simulation_tasks')
    op.drop_index(op.f('ix_simulations_slug'), table_name='simulations')
    op.drop_index(op.f('ix_simulations_id'), table_name='simulations')
    op.drop_table('simulations')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_companies_id'), table_name='companies')
    op.drop_table('companies')
    op.drop_index(op.f('ix_universities_id'), table_name='universities')
    op.drop_table('universities')
