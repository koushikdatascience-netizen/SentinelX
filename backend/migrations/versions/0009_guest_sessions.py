"""Isolated expiring guest sessions, never paid inference."""
from alembic import op
import sqlalchemy as sa
revision="0009"
down_revision="0008"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("users",sa.Column("is_demo",sa.Boolean(),nullable=False,server_default=sa.text("false")))
    op.create_table("demo_sessions",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("user_id",sa.String(36),sa.ForeignKey("users.id"),nullable=False,unique=True),
        sa.Column("ip_hash",sa.String(64),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_demo_sessions_user_id","demo_sessions",["user_id"],unique=True)
    op.create_index("ix_demo_sessions_ip_hash","demo_sessions",["ip_hash"])

def downgrade():
    op.drop_index("ix_demo_sessions_ip_hash",table_name="demo_sessions")
    op.drop_index("ix_demo_sessions_user_id",table_name="demo_sessions")
    op.drop_table("demo_sessions")
    op.drop_column("users","is_demo")
