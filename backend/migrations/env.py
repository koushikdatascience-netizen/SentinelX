"""Migration URL comes from server environment, never from a committed secret."""
import os
from alembic import context
from sqlalchemy import create_engine, pool
from app.workspace_store import Base
from app.budget import ApiBudget  # Register budget metadata.
from app import intelligence_store  # Register additive research/data metadata.

url = os.getenv("DATABASE_URL", "sqlite:///./sentinelx-dev.sqlite3")
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
