"""add cached_intents table

Revision ID: add_cached_intents_001
Revises: split_user_identity_001
Create Date: 2026-01-11 03:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_cached_intents_001'
down_revision = 'split_user_identity_001'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'cached_intents',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('intent_key', sa.String(), nullable=False),
        sa.Column('action_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_cached_intents_user_id', 'cached_intents', ['user_id'])
    op.create_index('ix_cached_intents_intent_key', 'cached_intents', ['intent_key'])

def downgrade():
    op.drop_table('cached_intents')
