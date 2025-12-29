"""add email integration fields

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2025-12-30 00:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add token fields to integrations
    op.add_column('integrations', sa.Column('gmail_token', sa.LargeBinary(), nullable=True))
    op.add_column('integrations', sa.Column('outlook_token', sa.LargeBinary(), nullable=True))
    
    # Add email_draft_id to notes
    op.add_column('notes', sa.Column('email_draft_id', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'email_draft_id')
    op.drop_column('integrations', 'outlook_token')
    op.drop_column('integrations', 'gmail_token')
