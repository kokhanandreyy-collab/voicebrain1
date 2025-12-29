"""add yandex tasks integration fields

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2025-12-30 00:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add yandex_tasks_token to integrations
    op.add_column('integrations', sa.Column('yandex_tasks_token', sa.LargeBinary(), nullable=True))
    
    # Add yandex_task_id to notes
    op.add_column('notes', sa.Column('yandex_task_id', sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column('notes', 'yandex_task_id')
    op.drop_column('integrations', 'yandex_tasks_token')
