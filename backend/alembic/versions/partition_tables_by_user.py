"""partition tables by user

Revision ID: partition_vx
Revises: manual_adaptive_prefs
Create Date: 2026-01-11 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR

# revision identifiers, used by Alembic.
revision: str = 'partition_vx'
down_revision: Union[str, Sequence[str], None] = 'manual_adaptive_prefs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Handle NoteEmbedding (add user_id, partition)
    # Rename old table
    op.rename_table('note_embeddings', 'note_embeddings_old')
    
    # Create new partitioned table
    # We must explicitly define columns because we are recreating it
    op.create_table(
        'note_embeddings',
        sa.Column('note_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False), # New column
        sa.Column('embedding', VECTOR(1536), nullable=True),
        sa.PrimaryKeyConstraint('note_id', 'user_id'), # Partition key must be part of PK
        sa.ForeignKeyConstraint(['note_id'], ['notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        postgresql_partition_by='HASH (user_id)'
    )
    
    # Create partitions (e.g. 10 partitions)
    for i in range(10):
        op.execute(f"CREATE TABLE note_embeddings_p{i} PARTITION OF note_embeddings FOR VALUES WITH (MODULUS 10, REMAINDER {i})")

    # Migrate data
    op.execute("""
        INSERT INTO note_embeddings (note_id, user_id, embedding)
        SELECT ne.note_id, n.user_id, ne.embedding
        FROM note_embeddings_old ne
        JOIN notes n ON ne.note_id = n.id
        WHERE n.user_id IS NOT NULL
    """)
    
    # Drop old table
    op.drop_table('note_embeddings_old')


    # 2. Handle LongTermMemory (partition)
    op.rename_table('long_term_memories', 'long_term_memories_old')
    
    op.create_table(
        'long_term_memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('importance_score', sa.Float(), default=8.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('archived_summary', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), default=1.0),
        sa.Column('source', sa.String(), default='fact'),
        sa.Column('embedding', VECTOR(1536), nullable=True),
        sa.PrimaryKeyConstraint('id', 'user_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        postgresql_partition_by='HASH (user_id)'
    )

    for i in range(10):
        op.execute(f"CREATE TABLE long_term_memories_p{i} PARTITION OF long_term_memories FOR VALUES WITH (MODULUS 10, REMAINDER {i})")

    op.execute("""
        INSERT INTO long_term_memories (
            id, user_id, summary_text, importance_score, created_at, 
            is_archived, archived_summary, confidence, source, embedding
        )
        SELECT 
            id, user_id, summary_text, importance_score, created_at, 
            is_archived, archived_summary, confidence, source, embedding
        FROM long_term_memories_old
    """)

    op.drop_table('long_term_memories_old')


def downgrade() -> None:
    # Revert NoteEmbedding
    op.rename_table('note_embeddings', 'note_embeddings_partitioned')
    op.create_table(
        'note_embeddings',
        sa.Column('note_id', sa.String(), nullable=False),
        sa.Column('embedding', VECTOR(1536), nullable=True),
        sa.PrimaryKeyConstraint('note_id'),
        sa.ForeignKeyConstraint(['note_id'], ['notes.id'], )
    )
    op.execute("""
        INSERT INTO note_embeddings (note_id, embedding)
        SELECT note_id, embedding FROM note_embeddings_partitioned
    """)
    # Drop partitions cascade? PG handles dropping parent drops partitions usually.
    op.execute("DROP TABLE note_embeddings_partitioned CASCADE")

    # Revert LongTermMemory
    op.rename_table('long_term_memories', 'ltm_partitioned')
    op.create_table(
        'long_term_memories',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey("users.id")),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('importance_score', sa.Float(), default=8.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('archived_summary', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), default=1.0),
        sa.Column('source', sa.String(), default='fact'),
        sa.Column('embedding', VECTOR(1536), nullable=True)
    )
    op.execute("""
        INSERT INTO long_term_memories SELECT * FROM ltm_partitioned
    """)
    op.execute("DROP TABLE ltm_partitioned CASCADE")
