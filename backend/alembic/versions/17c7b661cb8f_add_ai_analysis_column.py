"""add_ai_analysis_column

Revision ID: 17c7b661cb8f
Revises: eb4fe8deb7bc
Create Date: 2025-12-25 12:18:24.097890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17c7b661cb8f'
down_revision: Union[str, Sequence[str], None] = 'eb4fe8deb7bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('notes', sa.Column('ai_analysis', sa.JSON(), nullable=True, server_default='{}'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('notes', 'ai_analysis')
