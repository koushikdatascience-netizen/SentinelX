"""Owner-controlled campaign landing pages and consented leads."""
from alembic import op
import sqlalchemy as sa
revision="0006"
down_revision="0005"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("landing_pages",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("campaign_id",sa.String(36),sa.ForeignKey("campaign_projects.id"),nullable=False),
        sa.Column("slug",sa.String(64),nullable=False,unique=True),
        sa.Column("spec_json",sa.Text(),nullable=False),
        sa.Column("provenance",sa.String(24),nullable=False),
        sa.Column("published",sa.Boolean(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_landing_pages_campaign_id","landing_pages",["campaign_id"])
    op.create_index("ix_landing_pages_slug","landing_pages",["slug"],unique=True)
    op.create_table("landing_leads",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("page_id",sa.String(36),sa.ForeignKey("landing_pages.id"),nullable=False),
        sa.Column("name",sa.String(100),nullable=False),
        sa.Column("phone",sa.String(30),nullable=False),
        sa.Column("message",sa.Text(),nullable=False),
        sa.Column("ip_hash",sa.String(64),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_landing_leads_page_id","landing_leads",["page_id"])
    op.create_index("ix_landing_leads_ip_hash","landing_leads",["ip_hash"])

def downgrade():
    op.drop_index("ix_landing_leads_ip_hash",table_name="landing_leads")
    op.drop_index("ix_landing_leads_page_id",table_name="landing_leads")
    op.drop_table("landing_leads")
    op.drop_index("ix_landing_pages_slug",table_name="landing_pages")
    op.drop_index("ix_landing_pages_campaign_id",table_name="landing_pages")
    op.drop_table("landing_pages")
