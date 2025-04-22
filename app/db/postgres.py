import logging
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

# Convert the standard PostgreSQL URL to an async one for async operations
postgres_url = settings.SQLALCHEMY_DATABASE_URI
async_postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://") if postgres_url else None

# Create engines for both sync and async operations
try:
    if postgres_url:
        sync_engine = create_engine(
            postgres_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
        )
    
    if async_postgres_url:
        async_engine = create_async_engine(
            async_postgres_url,
            pool_pre_ping=True,
            pool_size=10, 
            max_overflow=20,
            pool_recycle=300,
        )
    
    # Create session factories
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine) if postgres_url else None
    AsyncSessionLocal = sessionmaker(class_=AsyncSession, autocommit=False, autoflush=False, bind=async_engine) if async_postgres_url else None
    
except Exception as e:
    logger.error(f"Failed to connect to PostgreSQL: {e}")
    raise DatabaseConnectionError(f"Could not connect to PostgreSQL: {e}")

# Create a Base class for SQLAlchemy models
Base = declarative_base()

def get_db() -> Generator:
    """
    Get a database session for the request
    """
    if not SessionLocal:
        raise DatabaseConnectionError("PostgreSQL connection is not configured")
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncSession:
    """
    Get an async database session
    """
    if not AsyncSessionLocal:
        raise DatabaseConnectionError("Async PostgreSQL connection is not configured")
        
    async with AsyncSessionLocal() as session:
        yield session

async def init_postgres():
    """
    Initialize PostgreSQL connection and create tables
    """
    logger.info("Initializing PostgreSQL connection")
    if postgres_url:
        # Create all tables in database
        Base.metadata.create_all(bind=sync_engine)
        logger.info("PostgreSQL connection initialized successfully")
    else:
        logger.warning("PostgreSQL connection string is not configured")
