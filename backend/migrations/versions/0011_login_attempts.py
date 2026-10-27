"""Add durable hashed-email login throttling."""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_attempts",
        sa.Column("email_key", sa.String(64), primary_key=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_login_attempts_window_started_at", "login_attempts", ["window_started_at"])


def downgrade():
    op.drop_index("ix_login_attempts_window_started_at", table_name="login_attempts")
    op.drop_table("login_attempts")
