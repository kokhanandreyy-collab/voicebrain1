"""add obsidian integration fields

Revision ID: a1b2c3d4e5f6
Revises: f3a2b1c0d9e8
Create Date: 2025-12-30 00:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f3a2b1c0d9e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add obsidian_vault_path to integrations
    op.add_column('integrations', sa.Column('obsidian_vault_path', sa.LargeBinary(), nullable=True))
    
    # Add obsidian_note_path to notes
    op.add_column('notes', sa.Column('obsidian_note_path', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'obsidian_note_path')
    op.drop_column('integrations', 'obsidian_vault_path')
