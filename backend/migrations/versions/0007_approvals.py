"""Audited approval decisions for campaign artifacts."""
from alembic import op
import sqlalchemy as sa
revision="0007"
down_revision="0006"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("landing_pages",sa.Column("approval_state",sa.String(24),nullable=False,server_default="proposed"))
    op.create_table("approval_records",
       sa.Column("id",sa.String(36),primary_key=True),
       sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
       sa.Column("campaign_id",sa.String(36),sa.ForeignKey("campaign_projects.id"),nullable=False),
       sa.Column("target_kind",sa.String(24),nullable=False),
       sa.Column("target_id",sa.String(36),nullable=False),
       sa.Column("state",sa.String(24),nullable=False),
       sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_approval_records_workspace_id","approval_records",["workspace_id"])
    op.create_index("ix_approval_records_campaign_id","approval_records",["campaign_id"])
    op.create_table("approval_events",
       sa.Column("id",sa.String(36),primary_key=True),
       sa.Column("approval_id",sa.String(36),sa.ForeignKey("approval_records.id"),nullable=False),
       sa.Column("reviewer_id",sa.String(36),sa.ForeignKey("users.id"),nullable=False),
       sa.Column("decision",sa.String(24),nullable=False),
       sa.Column("note",sa.Text(),nullable=False),
       sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_approval_events_approval_id","approval_events",["approval_id"])

def downgrade():
    op.drop_index("ix_approval_events_approval_id",table_name="approval_events")
    op.drop_table("approval_events")
    op.drop_index("ix_approval_records_campaign_id",table_name="approval_records")
    op.drop_index("ix_approval_records_workspace_id",table_name="approval_records")
    op.drop_table("approval_records")
    op.drop_column("landing_pages","approval_state")
