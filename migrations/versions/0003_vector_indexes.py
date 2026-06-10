"""Create the pgvector HNSW cosine index."""

from alembic import op

revision = "0003_vector_indexes"
down_revision = "0002_storage_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX issue_embeddings_hnsw
        ON issue_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS issue_embeddings_hnsw")
