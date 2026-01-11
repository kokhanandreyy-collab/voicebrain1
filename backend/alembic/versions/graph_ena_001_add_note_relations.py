"""add note_relations for graph ena

Revision ID: graph_ena_001
Revises: c306a2a50f23
Create Date: 2026-01-11 03:25:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'graph_ena_001'
down_revision = 'c306a2a50f23'
branch_labels = None
depends_on = None

def upgrade():
    # Ensure note_relations table exists with correct schema
    # Using DROP IF EXISTS for clean state in migration demo
    op.execute("DROP TABLE IF EXISTS note_relations")
    
    op.create_table(
        'note_relations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('note_id1', sa.String(), sa.ForeignKey('notes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_id2', sa.String(), sa.ForeignKey('notes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('strength', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_note_relations_id'), 'note_relations', ['id'], unique=False)

def downgrade():
    op.drop_table('note_relations')
