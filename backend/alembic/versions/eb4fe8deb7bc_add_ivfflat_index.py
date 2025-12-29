"""add_ivfflat_index

Revision ID: eb4fe8deb7bc
Revises: c972d77c2253
Create Date: 2025-12-25 00:50:15.694265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb4fe8deb7bc'
down_revision: Union[str, Sequence[str], None] = 'c972d77c2253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use op.execute for plain SQL
    # Ensure vector_cosine_ops is available (requires pgvector 0.4+)
    
    # Check if table exists before creating index
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'note_embeddings' in tables:
        op.execute("CREATE INDEX IF NOT EXISTS idx_note_embeddings_embedding ON note_embeddings USING hnsw (embedding vector_cosine_ops);")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS idx_note_embeddings_embedding;")
