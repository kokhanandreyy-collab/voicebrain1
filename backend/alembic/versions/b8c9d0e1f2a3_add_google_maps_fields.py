"""add google maps integration fields

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2025-12-29 23:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add google_maps_access_token to integrations
    op.add_column('integrations', sa.Column('google_maps_access_token', sa.LargeBinary(), nullable=True))
    
    # Add google_maps_url to notes
    op.add_column('notes', sa.Column('google_maps_url', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'google_maps_url')
    op.drop_column('integrations', 'google_maps_access_token')
