"""Additive relational storage for research, evidence facts and private datasets."""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import ForeignKey,String,Text,DateTime,Integer,LargeBinary,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from app.workspace_store import Base,utcnow


class ResearchJob(Base):
    __tablename__="research_jobs"
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id:Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    state:Mapped[str]=mapped_column(String(24),default="queued",index=True)
    payload_json:Mapped[str]=mapped_column(Text)
    lease_until:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)


class BusinessFact(Base):
    __tablename__="business_facts"
    __table_args__=(UniqueConstraint("workspace_id","fact_key",name="uq_business_fact_key"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id:Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    fact_key:Mapped[str]=mapped_column(String(64))
    kind:Mapped[str]=mapped_column(String(48))
    value_json:Mapped[str]=mapped_column(Text)
    evidence_json:Mapped[str]=mapped_column(Text)
    visibility:Mapped[str]=mapped_column(String(24),default="public")
    verification:Mapped[str]=mapped_column(String(32),default="source_observed")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)


class BusinessDataset(Base):
    __tablename__="business_datasets"
    __table_args__=(UniqueConstraint("workspace_id","filename","version",name="uq_dataset_version"),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id:Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    filename:Mapped[str]=mapped_column(String(180))
    version:Mapped[int]=mapped_column(Integer)
    sha256:Mapped[str]=mapped_column(String(64))
    mime:Mapped[str]=mapped_column(String(80))
    size:Mapped[int]=mapped_column(Integer)
    original:Mapped[bytes]=mapped_column(LargeBinary)
    analysis_json:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
