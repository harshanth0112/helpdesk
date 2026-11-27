from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Production (free-tier) uses a smaller pool to stay within Railway connection limits.
# Development keeps the larger pool for concurrent test runners.
_pool_size = 2 if settings.is_production else 10
_max_overflow = 3 if settings.is_production else 20

# Engine configuration with connection pooling
engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,         # Detect dead sockets before lending a connection
    pool_size=_pool_size,       # Steady-state connections kept open
    max_overflow=_max_overflow, # Temporary extra connections allowed above pool_size
    pool_recycle=1800,          # Recycle connections every 30 min (avoids stale TCP)
    pool_timeout=30,            # Raise after 30 s waiting for a free connection
    echo=settings.DEBUG,        # Log SQL only in debug mode — never in production
)

# Session factory configured with autocommit=False, autoflush=False
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False   # Prevents expired attribute errors after transaction commits
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Ensures safe transaction cleanup, rollback on exception, and session closure.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
