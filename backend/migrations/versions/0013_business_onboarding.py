"""Persist business onboarding, consent, bounded research and private assets."""
from alembic import op
import sqlalchemy as sa

revision="0013"
down_revision="0012"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table("business_profiles",
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),primary_key=True),
        sa.Column("details_json",sa.Text(),nullable=False),
        sa.Column("consent_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("consent_version",sa.String(32),nullable=False),
        sa.Column("completed_at",sa.DateTime(timezone=True),nullable=True),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("brand_research_jobs",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("request_id",sa.String(36),nullable=False),
        sa.Column("state",sa.String(24),nullable=False),
        sa.Column("input_json",sa.Text(),nullable=False),
        sa.Column("report_json",sa.Text(),nullable=False),
        sa.Column("lease_until",sa.DateTime(timezone=True),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("workspace_id","request_id",name="uq_brand_research_request"))
    for field in ("workspace_id","state"):
        op.create_index("ix_brand_research_jobs_"+field,"brand_research_jobs",[field])
    op.create_table("brand_assets",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("job_id",sa.String(36),sa.ForeignKey("brand_research_jobs.id"),nullable=True),
        sa.Column("kind",sa.String(32),nullable=False),
        sa.Column("filename",sa.String(180),nullable=False),
        sa.Column("mime",sa.String(100),nullable=False),
        sa.Column("sha256",sa.String(64),nullable=False),
        sa.Column("content",sa.LargeBinary(),nullable=False),
        sa.Column("source_url",sa.Text(),nullable=False),
        sa.Column("metadata_json",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("workspace_id","sha256","kind",name="uq_brand_asset_content"))
    op.create_index("ix_brand_assets_workspace_id","brand_assets",["workspace_id"])


def downgrade():
    raise RuntimeError("Business data is retained; destructive downgrade requires a reviewed recovery plan")
