"""Durable per-workspace campaign request attempt quota."""
from alembic import op
import sqlalchemy as sa
revision="0005"
down_revision="0004"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("campaign_quotas",
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),primary_key=True),
        sa.Column("attempts",sa.Integer(),nullable=False))
def downgrade():
    op.drop_table("campaign_quotas")
