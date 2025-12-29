"""add 2gis and mapsme integration fields

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2025-12-30 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add fields to integrations
    op.add_column('integrations', sa.Column('twogis_token', sa.LargeBinary(), nullable=True))
    op.add_column('integrations', sa.Column('mapsme_path', sa.LargeBinary(), nullable=True))
    
    # Add fields to notes
    op.add_column('notes', sa.Column('twogis_url', sa.String(), nullable=True))
    op.add_column('notes', sa.Column('mapsme_url', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'mapsme_url')
    op.drop_column('notes', 'twogis_url')
    op.drop_column('integrations', 'mapsme_path')
    op.drop_column('integrations', 'twogis_token')
