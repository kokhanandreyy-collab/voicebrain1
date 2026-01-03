"""add importance_score to notes manually

Revision ID: manual_001
Revises: a7b8c9d0e1f2
Create Date: 2026-01-03 15:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'manual_001'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add importance_score column to notes table
    op.add_column('notes', sa.Column('importance_score', sa.Float(), nullable=True, server_default='5.0'))

def downgrade() -> None:
    op.drop_column('notes', 'importance_score')
