"""update note_relations to integer pk

Revision ID: manual_graph_v2
Revises: manual_adaptive_prefs
Create Date: 2026-01-03 17:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'manual_graph_v2'
down_revision: Union[str, Sequence[str], None] = 'manual_adaptive_prefs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # We drop and recreate note_relations to switch ID type safely
    op.drop_table('note_relations')
    
    op.create_table(
        'note_relations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('note_id1', sa.String(), nullable=False),
        sa.Column('note_id2', sa.String(), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('strength', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['note_id1'], ['notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['note_id2'], ['notes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('note_relations')
    # Recreate generic string version if needed, or just leave dropped
    op.create_table(
        'note_relations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('note_id1', sa.String(), nullable=False),
        sa.Column('note_id2', sa.String(), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('strength', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['note_id1'], ['notes.id'], ),
        sa.ForeignKeyConstraint(['note_id2'], ['notes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
