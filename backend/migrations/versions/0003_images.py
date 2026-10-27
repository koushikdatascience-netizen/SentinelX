"""Workspace-scoped image score metadata; no image content retained."""
from alembic import op
import sqlalchemy as sa

revision="0003"
down_revision="0002"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("image_assessments",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("workspace_id",sa.String(36),sa.ForeignKey("workspaces.id"),nullable=False),
        sa.Column("filename",sa.String(180),nullable=False),
        sa.Column("assessment_json",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_image_assessments_workspace_id","image_assessments",["workspace_id"])

def downgrade():
    op.drop_index("ix_image_assessments_workspace_id",table_name="image_assessments")
    op.drop_table("image_assessments")
