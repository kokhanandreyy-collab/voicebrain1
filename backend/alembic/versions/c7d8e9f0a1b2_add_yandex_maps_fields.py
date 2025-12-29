"""add yandex maps integration fields

Revision ID: c7d8e9f0a1b2
Revises: b8c9d0e1f2a3
Create Date: 2025-12-30 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add yandex_maps_access_token to integrations
    op.add_column('integrations', sa.Column('yandex_maps_access_token', sa.LargeBinary(), nullable=True))
    
    # Add yandex_maps_url to notes
    op.add_column('notes', sa.Column('yandex_maps_url', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'yandex_maps_url')
    op.drop_column('integrations', 'yandex_maps_access_token')
