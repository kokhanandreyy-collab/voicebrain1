"""add tasks integration fields

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2025-12-30 00:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add token fields to integrations
    op.add_column('integrations', sa.Column('apple_reminders_token', sa.LargeBinary(), nullable=True))
    op.add_column('integrations', sa.Column('google_tasks_token', sa.LargeBinary(), nullable=True))
    
    # Add reminder_id to notes
    op.add_column('notes', sa.Column('reminder_id', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'reminder_id')
    op.drop_column('integrations', 'google_tasks_token')
    op.drop_column('integrations', 'apple_reminders_token')
