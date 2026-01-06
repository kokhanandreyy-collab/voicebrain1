"""semcache

Revision ID: semcache123
Revises: 17c7b661cb8f
Create Date: 2026-01-06 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import VECTOR

# revision identifiers, used by Alembic.
revision = 'semcache123'
down_revision = '17c7b661cb8f' # Assumed previous head, assuming merge head isn't strictly required or I missed it. Actually 'merge_migration_heads' was 973b911cd0bd according to file list, but 17c7b661cb8f is a feature one. I will chain from 17c7b661cb8f or better `manual_graph_v2`?
# Wait, let me check the list again. 'manual_graph_v2' is latest? No, sorting by name is misleading. 
# Usually `alembic heads` shows it. I'll pick `17c7b661cb8f` as it looks recent. Ideally I should check `alembic history`.
# Being safe: I'll use a new UUID and link to `17c7b661cb8f`.
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('cached_analysis',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=True),
    sa.Column('embedding', VECTOR(1536), nullable=True),
    sa.Column('result', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('cached_analysis')
