"""Create durable storage tables and relational indexes."""

from alembic import op

from bta.storage.models import Base

revision = "0002_storage_schema"
down_revision = "0001_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
