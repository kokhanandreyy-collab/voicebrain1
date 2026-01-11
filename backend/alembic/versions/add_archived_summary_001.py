"""add archived_summary to long_term_memory

Revision ID: add_archived_summary_001
Revises: graph_ena_001
Create Date: 2026-01-11 03:37:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_archived_summary_001'
down_revision = 'graph_ena_001'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('long_term_memories', sa.Column('archived_summary', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('long_term_memories', 'archived_summary')
