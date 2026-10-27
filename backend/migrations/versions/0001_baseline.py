"""Baseline before evidence generation quotas. Existing DBs require verified adoption."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("email", sa.String(255), nullable=False),
                    sa.Column("password_hash", sa.String(500), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("workspaces", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("name", sa.String(160), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])
    op.create_table("workflow_runs", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id"), nullable=False),
                    sa.Column("website", sa.Text(), nullable=False),
                    sa.Column("objective", sa.Text(), nullable=False),
                    sa.Column("status", sa.String(30), nullable=False),
                    sa.Column("result_json", sa.Text(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_workflow_runs_workspace_id", "workflow_runs", ["workspace_id"])
    op.create_table("reviewable_actions", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("run_id", sa.String(36), sa.ForeignKey("workflow_runs.id"), nullable=False),
                    sa.Column("description", sa.Text(), nullable=False),
                    sa.Column("state", sa.String(24), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_reviewable_actions_run_id", "reviewable_actions", ["run_id"])
    op.create_table("api_budgets", sa.Column("provider", sa.String(40), primary_key=True),
                    sa.Column("reserved_cents", sa.Integer(), nullable=False))


def downgrade():
    # Destructive downgrades must be a deliberate operator action with backups.
    for name in ("api_budgets", "reviewable_actions", "workflow_runs", "workspaces", "users"):
        op.drop_table(name)
