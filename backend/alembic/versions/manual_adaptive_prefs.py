"""add adaptive_preferences to users

Revision ID: manual_adaptive_prefs
Revises: manual_relations
Create Date: 2026-01-03 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'manual_adaptive_prefs'
down_revision: Union[str, Sequence[str], None] = 'manual_relations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add column adaptive_preferences to users table
    # Using JSON type (sa.JSON generic, maps to JSONB in PG usually if engine allows, or use JSONB explicit)
    op.add_column('users', sa.Column('adaptive_preferences', sa.JSON(), nullable=True, server_default='{}'))

def downgrade() -> None:
    op.drop_column('users', 'adaptive_preferences')
