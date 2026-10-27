"""Meta capability verification metadata."""
from alembic import op
import sqlalchemy as sa
revision="0010"
down_revision="0009"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("meta_capability_checks",
        sa.Column("capability",sa.String(32),primary_key=True),
        sa.Column("model",sa.String(100),nullable=False),
        sa.Column("succeeded_at",sa.DateTime(timezone=True),nullable=False))
def downgrade():
    op.drop_table("meta_capability_checks")
