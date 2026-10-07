"""0011_scenario_engine

Ssenariy dvigateli jadvallari va submissions kengaytmasi (CONTRACT.md §9.7).

Revision ID: 74949275f108
Revises: 781635ae405f
Create Date: 2026-10-07 10:01:01.278875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '74949275f108'
down_revision: Union[str, Sequence[str], None] = '781635ae405f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # §9.4 — document_chunks.embedding. Docker'da POSTGRES_USER superuser;
    # managed Postgres'da extension oldindan yoqilgan bo'lishi kerak.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('scenarios',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('sector', sa.Enum('IT', 'Banking', name='sector', native_enum=False), nullable=False),
    sa.Column('company_name', sa.String(length=120), nullable=False),
    sa.Column('difficulty', sa.String(length=20), nullable=False),
    sa.Column('duration_days', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('work_holidays',
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('source', sa.Enum('auto', 'manual', name='holidaysource', native_enum=False), nullable=False),
    sa.PrimaryKeyConstraint('date')
    )
    op.create_table('scenario_versions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('scenario_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'published', 'archived', name='scenarioversionstatus', native_enum=False), nullable=False),
    sa.Column('definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('scenario_id', 'version', name='uq_scenario_versions_version')
    )
    op.create_table('runs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('scenario_version_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('scheduled', 'active', 'completed', 'expired', 'abandoned', name='runstatus', native_enum=False), nullable=False),
    sa.Column('start_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('ai_tokens_used', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('competency_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('final_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['scenario_version_id'], ['scenario_versions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_runs_status_ends_at', 'runs', ['status', 'ends_at'], unique=False)
    op.create_index('ix_runs_user_id', 'runs', ['user_id'], unique=False)
    op.create_index('uq_runs_one_open_per_version', 'runs', ['user_id', 'scenario_version_id'], unique=True, postgresql_where=sa.text("status IN ('scheduled', 'active')"))
    op.create_table('scenario_documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('scenario_version_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('visible_to_personas', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['scenario_version_id'], ['scenario_versions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('scenario_version_id', 'key', name='uq_scenario_documents_key')
    )
    op.create_table('document_chunks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(768), nullable=True),
    sa.Column('embedding_model', sa.String(length=80), nullable=True),
    sa.Column('tsv', postgresql.TSVECTOR(), sa.Computed("to_tsvector('simple', text)", persisted=True), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['scenario_documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunks_index')
    )
    op.create_index('ix_document_chunks_embedding', 'document_chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_document_chunks_tsv', 'document_chunks', ['tsv'], unique=False, postgresql_using='gin')
    op.create_table('run_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('node_id', sa.String(length=64), nullable=False),
    sa.Column('status', sa.Enum('pending', 'delivered', 'submitted', 'missed', 'skipped', name='runeventstatus', native_enum=False), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('first_opened_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('choice', sa.String(length=64), nullable=True),
    sa.Column('hints_used', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('run_id', 'node_id', name='uq_run_events_node')
    )
    op.create_index('ix_run_events_status_due_at', 'run_events', ['status', 'due_at'], unique=False)
    op.create_index('ix_run_events_status_scheduled_at', 'run_events', ['status', 'scheduled_at'], unique=False)
    op.create_table('uploaded_files',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('owner_user_id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=True),
    sa.Column('stored_path', sa.String(length=500), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('mime', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('run_id', sa.UUID(), nullable=False),
    sa.Column('persona_key', sa.String(length=64), nullable=False),
    sa.Column('sender', sa.Enum('student', 'persona', 'system', name='chatsender', native_enum=False), nullable=False),
    sa.Column('content_type', sa.Enum('text', 'file', 'link', 'voice', 'image', 'video', name='chatcontenttype', native_enum=False), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('file_id', sa.UUID(), nullable=True),
    sa.Column('link_url', sa.String(length=2048), nullable=True),
    sa.Column('generated', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['uploaded_files.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_thread', 'chat_messages', ['run_id', 'persona_key', 'created_at'], unique=False)
    op.add_column('submissions', sa.Column('run_id', sa.UUID(), nullable=True))
    op.add_column('submissions', sa.Column('run_event_id', sa.UUID(), nullable=True))
    op.add_column('submissions', sa.Column('attempt', sa.SmallInteger(), server_default=sa.text('1'), nullable=False))
    op.add_column('submissions', sa.Column('late', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('submissions', sa.Column('rubric_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('submissions', sa.Column('file_id', sa.UUID(), nullable=True))
    op.add_column('submissions', sa.Column('link_url', sa.String(length=2048), nullable=True))
    op.alter_column('submissions', 'task_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_index('ix_submissions_run_id', 'submissions', ['run_id'], unique=False)
    op.create_index('uq_submissions_run_event_attempt', 'submissions', ['run_event_id', 'attempt'], unique=True, postgresql_where=sa.text('run_event_id IS NOT NULL'))
    op.create_foreign_key('fk_submissions_run_event_id', 'submissions', 'run_events', ['run_event_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_submissions_file_id', 'submissions', 'uploaded_files', ['file_id'], ['id'])
    op.create_foreign_key('fk_submissions_run_id', 'submissions', 'runs', ['run_id'], ['id'], ondelete='CASCADE')
    # Eski (task_id bilan) yozuvlar shartni allaqachon qanoatlantiradi.
    op.create_check_constraint('ck_submissions_target', 'submissions', '(task_id IS NULL) <> (run_event_id IS NULL)')


def downgrade() -> None:
    """Downgrade schema."""
    # Run submission'lari (task_id IS NULL) task_id NOT NULL'ga qaytib bo'lmaydi.
    op.execute("DELETE FROM submissions WHERE task_id IS NULL")
    op.drop_constraint('ck_submissions_target', 'submissions', type_='check')
    op.drop_constraint('fk_submissions_run_id', 'submissions', type_='foreignkey')
    op.drop_constraint('fk_submissions_file_id', 'submissions', type_='foreignkey')
    op.drop_constraint('fk_submissions_run_event_id', 'submissions', type_='foreignkey')
    op.drop_index('uq_submissions_run_event_attempt', table_name='submissions', postgresql_where=sa.text('run_event_id IS NOT NULL'))
    op.drop_index('ix_submissions_run_id', table_name='submissions')
    op.alter_column('submissions', 'task_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('submissions', 'link_url')
    op.drop_column('submissions', 'file_id')
    op.drop_column('submissions', 'rubric_scores')
    op.drop_column('submissions', 'late')
    op.drop_column('submissions', 'attempt')
    op.drop_column('submissions', 'run_event_id')
    op.drop_column('submissions', 'run_id')
    op.drop_index('ix_chat_messages_thread', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_table('uploaded_files')
    op.drop_index('ix_run_events_status_scheduled_at', table_name='run_events')
    op.drop_index('ix_run_events_status_due_at', table_name='run_events')
    op.drop_table('run_events')
    op.drop_index('ix_document_chunks_tsv', table_name='document_chunks', postgresql_using='gin')
    op.drop_index('ix_document_chunks_embedding', table_name='document_chunks', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_table('document_chunks')
    op.drop_table('scenario_documents')
    op.drop_index('uq_runs_one_open_per_version', table_name='runs', postgresql_where=sa.text("status IN ('scheduled', 'active')"))
    op.drop_index('ix_runs_user_id', table_name='runs')
    op.drop_index('ix_runs_status_ends_at', table_name='runs')
    op.drop_table('runs')
    op.drop_table('scenario_versions')
    op.drop_table('work_holidays')
    op.drop_table('scenarios')
