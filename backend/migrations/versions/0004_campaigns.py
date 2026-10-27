"""Campaign audits and seven-day items (no publishing)."""
from alembic import op
import sqlalchemy as sa

revision="0004"
down_revision="0003"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("campaign_projects",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("business_description",sa.Text(),nullable=False),
        sa.Column("goal",sa.Text(),nullable=False),
        sa.Column("language",sa.String(2),nullable=False),
        sa.Column("audit_json",sa.Text(),nullable=False),
        sa.Column("provenance",sa.String(24),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_campaign_projects_workspace_id","campaign_projects",["workspace_id"])
    op.create_table("campaign_items",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("campaign_id",sa.String(36),sa.ForeignKey("campaign_projects.id"),nullable=False),
        sa.Column("day",sa.Integer(),nullable=False),
        sa.Column("platform",sa.String(24),nullable=False),
        sa.Column("item_json",sa.Text(),nullable=False),
        sa.Column("provenance",sa.String(24),nullable=False),
        sa.Column("state",sa.String(24),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_campaign_items_campaign_id","campaign_items",["campaign_id"])

def downgrade():
    op.drop_index("ix_campaign_items_campaign_id",table_name="campaign_items")
    op.drop_table("campaign_items")
    op.drop_index("ix_campaign_projects_workspace_id",table_name="campaign_projects")
    op.drop_table("campaign_projects")
