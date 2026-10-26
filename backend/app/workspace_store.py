"""SQLAlchemy-backed tenant-isolated workspaces and persisted workflow records."""
import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, ForeignKey, String, Text, DateTime, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

def utcnow(): return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    email: Mapped[str] = mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str] = mapped_column(String(500))
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
def init_db(): Base.metadata.create_all(engine)
def session():
    with SessionLocal() as db:
        yield db
