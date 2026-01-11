"""split user identity into stable and volatile

Revision ID: split_user_identity_001
Revises: add_archived_summary_001
Create Date: 2026-01-11 03:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'split_user_identity_001'
down_revision = 'add_archived_summary_001'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('stable_identity', sa.Text(), server_default='', nullable=True))
    op.add_column('users', sa.Column('volatile_preferences', sa.JSON(), server_default='{}', nullable=True))

def downgrade():
    op.drop_column('users', 'volatile_preferences')
    op.drop_column('users', 'stable_identity')
