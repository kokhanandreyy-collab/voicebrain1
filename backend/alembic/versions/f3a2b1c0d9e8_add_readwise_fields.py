"""add readwise integration fields

Revision ID: f3a2b1c0d9e8
Revises: e9f0a1b2c3d4
Create Date: 2025-12-30 00:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f3a2b1c0d9e8'
down_revision: Union[str, Sequence[str], None] = 'e9f0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add token fields to integrations
    op.add_column('integrations', sa.Column('readwise_token', sa.LargeBinary(), nullable=True))
    
    # Add readwise_highlight_id to notes
    op.add_column('notes', sa.Column('readwise_highlight_id', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'readwise_highlight_id')
    op.drop_column('integrations', 'readwise_token')
