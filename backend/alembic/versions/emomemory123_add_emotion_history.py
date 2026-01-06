"""add emotion history

Revision ID: emomemory123
Revises: semcache123
Create Date: 2026-01-06 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'emomemory123'
down_revision = 'semcache123'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('emotion_history', sa.JSON(), nullable=True, server_default='[]'))


def downgrade() -> None:
    op.drop_column('users', 'emotion_history')
