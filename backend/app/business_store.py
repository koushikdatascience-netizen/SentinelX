"""Private business profiles, durable research jobs and source asset bytes."""
from uuid import uuid4
from sqlalchemy import ForeignKey,String,Text,DateTime,LargeBinary,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.workspace_store import Base,utcnow


class BusinessProfile(Base):
    __tablename__="business_profiles"
    workspace_id:Mapped[str]=mapped_column(ForeignKey("workspaces.id"),primary_key=True)
    details_json:Mapped[str]=mapped_column(Text,default="{}")
    consent_at:Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    consent_version:Mapped[str]=mapped_column(String(32),default="")
    completed_at:Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    updated_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=utcnow)


class BrandResearchJob(Base):
    __tablename__="brand_research_jobs"
    __table_args__=(UniqueConstraint("workspace_id","request_id",name="uq_brand_research_request"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id:Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    request_id:Mapped[str]=mapped_column(String(36))
    state:Mapped[str]=mapped_column(String(24),default="queued",index=True)
    input_json:Mapped[str]=mapped_column(Text)
    report_json:Mapped[str]=mapped_column(Text,default="{}")
    lease_until:Mapped[object|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=utcnow)


class BrandAsset(Base):
    __tablename__="brand_assets"
    __table_args__=(UniqueConstraint("workspace_id","sha256","kind",name="uq_brand_asset_content"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id:Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    job_id:Mapped[str|None]=mapped_column(ForeignKey("brand_research_jobs.id"),nullable=True)
    kind:Mapped[str]=mapped_column(String(32))
    filename:Mapped[str]=mapped_column(String(180))
    mime:Mapped[str]=mapped_column(String(100))
    sha256:Mapped[str]=mapped_column(String(64))
    content:Mapped[bytes]=mapped_column(LargeBinary)
    source_url:Mapped[str]=mapped_column(Text,default="")
    metadata_json:Mapped[str]=mapped_column(Text,default="{}")
    created_at:Mapped[object]=mapped_column(DateTime(timezone=True),default=utcnow)
