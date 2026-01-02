"""merge_migration_heads

Revision ID: 973b911cd0bd
Revises: 2d12cdb45a52, c4d5e6f7a8b9
Create Date: 2026-01-03 01:01:12.291271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '973b911cd0bd'
down_revision: Union[str, Sequence[str], None] = ('2d12cdb45a52', 'c4d5e6f7a8b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
