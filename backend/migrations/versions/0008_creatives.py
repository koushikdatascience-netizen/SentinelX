"""Campaign creative image variants stored as bounded bytes."""
from alembic import op
import sqlalchemy as sa
revision="0008"
down_revision="0007"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("campaign_creatives",
        sa.Column("id",sa.String(36),primary_key=True),
        sa.Column("campaign_id",sa.String(36),sa.ForeignKey("campaign_projects.id"),nullable=False),
        sa.Column("item_id",sa.String(36),sa.ForeignKey("campaign_items.id"),nullable=False),
        sa.Column("prompt",sa.Text(),nullable=False),
        sa.Column("mime",sa.String(30),nullable=False),
        sa.Column("image_blob",sa.LargeBinary(),nullable=False),
        sa.Column("scores_json",sa.Text(),nullable=False),
        sa.Column("provenance",sa.String(24),nullable=False),
        sa.Column("selected",sa.Boolean(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_campaign_creatives_campaign_id","campaign_creatives",["campaign_id"])
    op.create_index("ix_campaign_creatives_item_id","campaign_creatives",["item_id"])
def downgrade():
    op.drop_index("ix_campaign_creatives_item_id",table_name="campaign_creatives")
    op.drop_index("ix_campaign_creatives_campaign_id",table_name="campaign_creatives")
    op.drop_table("campaign_creatives")
