"""merge_heads_for_graph

Revision ID: c306a2a50f23
Revises: 973b911cd0bd, emomemory123, manual_graph_memory
Create Date: 2026-01-06 23:15:24.472097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c306a2a50f23'
down_revision: Union[str, Sequence[str], None] = ('973b911cd0bd', 'emomemory123', 'manual_graph_memory')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
