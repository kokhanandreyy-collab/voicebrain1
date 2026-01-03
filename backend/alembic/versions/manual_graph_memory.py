"""create note_relations table

Revision ID: manual_graph_memory
Revises: manual_graph_v2
Create Date: 2026-01-03 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'manual_graph_memory'
down_revision = 'manual_graph_v2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Drop existing if any from previous manual steps to ensure clean state
    op.execute("DROP TABLE IF EXISTS note_relations")
    
    op.create_table(
        'note_relations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True, autoincrement=True),
        sa.Column('note_id1', sa.String(), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column('note_id2', sa.String(), sa.ForeignKey("notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=True),
        sa.Column('strength', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True)
    )

def downgrade() -> None:
    op.drop_table('note_relations')
