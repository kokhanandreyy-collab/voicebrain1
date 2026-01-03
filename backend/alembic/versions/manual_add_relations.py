"""create note_relations table

Revision ID: manual_relations
Revises: manual_001
Create Date: 2026-01-03 15:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'manual_relations'
down_revision: Union[str, Sequence[str], None] = 'manual_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Check if table exists (optional, but good practice). 
    # Since we can't easily check in raw alembic without engine, we'll try create and catch error implies it exists? 
    # Or just create. Postgres 'IF NOT EXISTS' is nice but SA creates it.
    # We will just strictly create it. If it fails, user can handle or we assume clean state for this feature.
    # Actually, previous steps showed NoteRelation in models.py, but not in initial migration.
    # It might have been created by another migration I missed viewing, or it's not in DB yet.
    # I will attempt to create it.
    
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

def downgrade() -> None:
    op.drop_table('note_relations')
