"""Add lifetime workspace request quota; no existing records are rewritten."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("evidence_quotas",
                    sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), primary_key=True),
                    sa.Column("attempts", sa.Integer(), nullable=False))


def downgrade():
    op.drop_table("evidence_quotas")
