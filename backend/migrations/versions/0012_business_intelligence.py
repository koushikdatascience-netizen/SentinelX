"""Add research checkpoints, structured evidence facts and private datasets.

Additive and compatible with the previous application. Roll back application
containers first; retain these tables. Downgrade is destructive and manual only.
"""
from alembic import op
import sqlalchemy as sa

revision="0012"
down_revision="0011"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table("research_jobs",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("state",sa.String(24),nullable=False),
        sa.Column("payload_json",sa.Text(),nullable=False),
        sa.Column("lease_until",sa.DateTime(timezone=True),nullable=True),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_research_jobs_workspace_id","research_jobs",["workspace_id"])
    op.create_index("ix_research_jobs_state","research_jobs",["state"])
    op.create_table("business_facts",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("fact_key",sa.String(64),nullable=False),
        sa.Column("kind",sa.String(48),nullable=False),
        sa.Column("value_json",sa.Text(),nullable=False),
        sa.Column("evidence_json",sa.Text(),nullable=False),
        sa.Column("visibility",sa.String(24),nullable=False),
        sa.Column("verification",sa.String(32),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("workspace_id","fact_key",name="uq_business_fact_key"))
    op.create_index("ix_business_facts_workspace_id","business_facts",["workspace_id"])
    op.create_table("business_datasets",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("filename",sa.String(180),nullable=False),
        sa.Column("version",sa.Integer(),nullable=False),
        sa.Column("sha256",sa.String(64),nullable=False),
        sa.Column("mime",sa.String(80),nullable=False),
        sa.Column("size",sa.Integer(),nullable=False),
        sa.Column("original",sa.LargeBinary(),nullable=False),
        sa.Column("analysis_json",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("workspace_id","filename","version",name="uq_dataset_version"))
    op.create_index("ix_business_datasets_workspace_id","business_datasets",["workspace_id"])


def downgrade():
    op.drop_table("business_datasets")
    op.drop_table("business_facts")
    op.drop_table("research_jobs")
