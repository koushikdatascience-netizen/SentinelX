"""SQLAlchemy-backed tenant-isolated workspaces and persisted workflow records."""
import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, ForeignKey, String, Text, DateTime, Integer, LargeBinary, select, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

def utcnow(): return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    email: Mapped[str] = mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str] = mapped_column(String(500))
    is_demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"),index=True)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"),index=True)
    website: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30),default="proposed")
    result_json: Mapped[str] = mapped_column(Text,default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./sentinelx-dev.sqlite3")
engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {},poolclass=StaticPool if DATABASE_URL=="sqlite:///:memory:" else None,pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,expire_on_commit=False)
def init_db():
    if os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true":
        Base.metadata.create_all(engine)
def session():
    with SessionLocal() as db:
        yield db

class ReviewableAction(Base):
    __tablename__ = "reviewable_actions"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"),index=True)
    description: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(24),default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True)

class EvidenceQuota(Base):
    """Lifetime attempt quota for the opt-in evidence draft operation."""
    __tablename__ = "evidence_quotas"
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

class ImageAssessment(Base):
    """Metadata and validated scores only. Raw uploaded image is not retained."""
    __tablename__ = "image_assessments"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"),index=True)
    filename: Mapped[str] = mapped_column(String(180))
    assessment_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

class CampaignProject(Base):
    __tablename__ = "campaign_projects"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"),index=True)
    business_description: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(2))
    audit_json: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(String(24),default="sample")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

class CampaignItem(Base):
    __tablename__ = "campaign_items"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaign_projects.id"),index=True)
    day: Mapped[int] = mapped_column(Integer)
    platform: Mapped[str] = mapped_column(String(24))
    item_json: Mapped[str] = mapped_column(Text)
    provenance: Mapped[str] = mapped_column(String(24),default="sample")
    state: Mapped[str] = mapped_column(String(24),default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=utcnow)

class CampaignQuota(Base):
    """Lifetime upper bound on two-call campaign generation attempts per workspace."""
    __tablename__="campaign_quotas"
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),primary_key=True)
    attempts: Mapped[int]=mapped_column(Integer,default=0)

class LandingPage(Base):
    __tablename__="landing_pages"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    campaign_id: Mapped[str]=mapped_column(ForeignKey("campaign_projects.id"),index=True)
    slug: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    spec_json: Mapped[str]=mapped_column(Text)
    provenance: Mapped[str]=mapped_column(String(24),default="sample")
    published: Mapped[bool]=mapped_column(default=False)
    approval_state: Mapped[str]=mapped_column(String(24),default="proposed")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class LandingLead(Base):
    __tablename__="landing_leads"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    page_id: Mapped[str]=mapped_column(ForeignKey("landing_pages.id"),index=True)
    name: Mapped[str]=mapped_column(String(100))
    phone: Mapped[str]=mapped_column(String(30))
    message: Mapped[str]=mapped_column(Text)
    ip_hash: Mapped[str]=mapped_column(String(64),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class ApprovalRecord(Base):
    __tablename__="approval_records"
    __table_args__=(UniqueConstraint("target_kind","target_id",name="uq_approval_target"),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    workspace_id: Mapped[str]=mapped_column(ForeignKey("workspaces.id"),index=True)
    campaign_id: Mapped[str]=mapped_column(ForeignKey("campaign_projects.id"),index=True)
    target_kind: Mapped[str]=mapped_column(String(24))
    target_id: Mapped[str]=mapped_column(String(36))
    state: Mapped[str]=mapped_column(String(24),default="proposed")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class ApprovalEvent(Base):
    __tablename__="approval_events"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    approval_id: Mapped[str]=mapped_column(ForeignKey("approval_records.id"),index=True)
    reviewer_id: Mapped[str]=mapped_column(ForeignKey("users.id"))
    decision: Mapped[str]=mapped_column(String(24))
    note: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class CampaignCreative(Base):
    __tablename__="campaign_creatives"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    campaign_id: Mapped[str]=mapped_column(ForeignKey("campaign_projects.id"),index=True)
    item_id: Mapped[str]=mapped_column(ForeignKey("campaign_items.id"),index=True)
    prompt: Mapped[str]=mapped_column(Text)
    mime: Mapped[str]=mapped_column(String(30))
    image_blob: Mapped[bytes]=mapped_column(LargeBinary)
    scores_json: Mapped[str]=mapped_column(Text)
    provenance: Mapped[str]=mapped_column(String(24))
    selected: Mapped[bool]=mapped_column(default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class DemoSession(Base):
    __tablename__="demo_sessions"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    user_id: Mapped[str]=mapped_column(ForeignKey("users.id"),unique=True,index=True)
    ip_hash: Mapped[str]=mapped_column(String(64),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))

class MetaCapabilityCheck(Base):
    """Metadata only, recorded after a real successful server-side Meta SDK call."""
    __tablename__="meta_capability_checks"
    capability: Mapped[str]=mapped_column(String(32),primary_key=True)
    model: Mapped[str]=mapped_column(String(100))
    succeeded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class LoginAttempt(Base):
    """Hashed-email login throttling shared across app workers."""
    __tablename__="login_attempts"
    email_key: Mapped[str]=mapped_column(String(64),primary_key=True)
    window_started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True,default=utcnow)
    attempts: Mapped[int]=mapped_column(Integer,default=0)
    locked_until: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
