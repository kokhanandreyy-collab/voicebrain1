"""add scope to cached_analysis

Revision ID: add_scope_cache_001
Revises: partition_vx
Create Date: 2026-01-11 17:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_scope_cache_001'
down_revision: Union[str, Sequence[str], None] = 'partition_vx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('cached_analysis', sa.Column('scope', sa.String(), nullable=True, server_default='general'))
    op.create_index(op.f('ix_cached_analysis_scope'), 'cached_analysis', ['scope'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_cached_analysis_scope'), table_name='cached_analysis')
    op.drop_column('cached_analysis', 'scope')
