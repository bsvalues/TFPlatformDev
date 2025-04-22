import os
import logging
from typing import Dict, Any, Optional
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import pyodbc
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

# Create Base class for SQLAlchemy models
Base = declarative_base()

# PostgreSQL connection
def get_postgres_connection_string() -> str:
    """
    Construct the PostgreSQL connection string from environment variables
    """
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "")
    database = os.getenv("PGDATABASE", "terrafusion")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

# Create PostgreSQL engine with connection pooling
postgres_engine = create_engine(
    get_postgres_connection_string(),
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=postgres_engine)

@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions to ensure proper cleanup
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        session.close()

# SQL Server connection (JCHARRISPACS)
def get_sqlserver_connection():
    """
    Create a connection to JCHARRISPACS SQL Server using Windows authentication
    """
    try:
        # Get connection string from environment variable
        conn_str = os.getenv("JCHARRISPACS_CONN", "")
        if not conn_str:
            # If not specified, build it from components
            server = os.getenv("JCHARRISPACS_SERVER", "")
            database = os.getenv("JCHARRISPACS_DATABASE", "")
            if not server or not database:
                raise ValueError("SQL Server connection parameters not provided")
            
            # Using Windows Authentication (Trusted Connection)
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
            
        # Create connection
        connection = pyodbc.connect(conn_str, autocommit=True)
        return connection
    except Exception as e:
        logger.error(f"SQL Server connection error: {str(e)}")
        raise

@contextmanager
def get_sqlserver_cursor():
    """
    Context manager for SQL Server connection to ensure proper cleanup
    """
    connection = None
    try:
        connection = get_sqlserver_connection()
        cursor = connection.cursor()
        yield cursor
    except Exception as e:
        logger.error(f"SQL Server cursor error: {str(e)}")
        raise
    finally:
        if connection:
            connection.close()

# Database initialization function
def init_database():
    """
    Initialize database tables and setup
    """
    try:
        # Create all tables defined in SQLAlchemy models
        Base.metadata.create_all(bind=postgres_engine)
        logger.info("PostgreSQL database tables created successfully")
        
        # Test SQL Server connection
        with get_sqlserver_cursor() as cursor:
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()
            logger.info(f"Connected to SQL Server: {version[0]}")
            
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

# Execute spatial query on PostGIS
def execute_spatial_query(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a spatial query on PostGIS and return the results
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        Query results as dictionary
    """
    try:
        with get_db_session() as session:
            result = session.execute(text(query), params or {})
            # Convert to list of dicts
            column_names = result.keys()
            rows = [dict(zip(column_names, row)) for row in result.fetchall()]
            return {"status": "success", "data": rows}
    except Exception as e:
        logger.error(f"Spatial query error: {str(e)}")
        return {"status": "error", "message": str(e)}

# Execute query on JCHARRISPACS
def execute_jcharrispacs_query(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute a query on JCHARRISPACS SQL Server and return the results
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        Query results as dictionary
    """
    try:
        with get_sqlserver_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Check if the query returns results
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return {"status": "success", "data": rows}
            else:
                return {"status": "success", "message": "Query executed successfully"}
    except Exception as e:
        logger.error(f"JCHARRISPACS query error: {str(e)}")
        return {"status": "error", "message": str(e)}
