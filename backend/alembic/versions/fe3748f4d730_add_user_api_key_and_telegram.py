"""add_user_api_key_and_telegram

Revision ID: fe3748f4d730
Revises: 17c7b661cb8f
Create Date: 2025-12-25 12:20:16.548942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe3748f4d730'
down_revision: Union[str, Sequence[str], None] = '17c7b661cb8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('api_key', sa.String(), nullable=True))
    op.add_column('users', sa.Column('telegram_chat_id', sa.String(), nullable=True))
    
    # Generate API keys for existing users
    import uuid
    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id FROM users")).fetchall()
    for user in users:
        new_key = str(uuid.uuid4())
        connection.execute(sa.text("UPDATE users SET api_key = :key WHERE id = :id"), {"key": new_key, "id": user.id})

    # Create indexes after population
    op.create_index(op.f('ix_users_api_key'), 'users', ['api_key'], unique=True)
    op.create_index(op.f('ix_users_telegram_chat_id'), 'users', ['telegram_chat_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_telegram_chat_id'), table_name='users')
    op.drop_index(op.f('ix_users_api_key'), table_name='users')
    op.drop_column('users', 'telegram_chat_id')
    op.drop_column('users', 'api_key')
