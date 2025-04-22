import logging
import os
from typing import Dict, Generator, Optional

import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from app.core.config import settings
from app.core.exceptions import SQLServerConnectionError

logger = logging.getLogger(__name__)

# SQL Server connection pool
sql_server_engine: Optional[Engine] = None

def get_sqlserver_connection_string() -> str:
    """
    Get the connection string for SQL Server, using Windows Authentication
    """
    conn_string = settings.SQLSERVER_CONN_STRING
    
    # If not explicitly set, try to build a connection string with Windows Auth
    if not conn_string:
        server = os.environ.get("SQLSERVER_SERVER", "localhost")
        database = os.environ.get("SQLSERVER_DATABASE", "master")
        
        # Use Windows Authentication
        conn_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
        
    return conn_string

def init_sqlserver_engine() -> Engine:
    """
    Initialize SQL Server connection engine with connection pooling
    """
    conn_string = get_sqlserver_connection_string()
    
    try:
        # Create engine with connection pooling
        engine = create_engine(
            f"mssql+pyodbc:///?odbc_connect={conn_string}",
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=300,
            pool_pre_ping=True,
        )
        
        # Test connection
        with engine.connect() as connection:
            connection.execute("SELECT 1")
            
        logger.info("SQL Server connection successful")
        return engine
        
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server: {e}")
        raise SQLServerConnectionError(f"Could not connect to SQL Server: {e}")

def get_sqlserver_conn() -> Generator:
    """
    Get a SQL Server connection from the pool
    """
    global sql_server_engine
    
    if not sql_server_engine:
        raise SQLServerConnectionError("SQL Server connection is not initialized")
        
    connection = sql_server_engine.connect()
    try:
        yield connection
    finally:
        connection.close()
        
async def execute_sqlserver_query(query: str, params: Optional[Dict] = None) -> list:
    """
    Execute a query against SQL Server
    """
    global sql_server_engine
    
    if not sql_server_engine:
        raise SQLServerConnectionError("SQL Server connection is not initialized")
    
    try:
        with sql_server_engine.connect() as connection:
            if params:
                result = connection.execute(query, **params)
            else:
                result = connection.execute(query)
                
            return [dict(row) for row in result]
    except Exception as e:
        logger.error(f"SQL Server query error: {e}")
        raise SQLServerConnectionError(f"Error executing SQL Server query: {e}")

async def init_sqlserver():
    """
    Initialize SQL Server connection
    """
    global sql_server_engine
    
    logger.info("Initializing SQL Server connection")
    try:
        sql_server_engine = init_sqlserver_engine()
        logger.info("SQL Server connection initialized successfully")
    except SQLServerConnectionError as e:
        logger.warning(f"SQL Server connection failed: {e}")
        logger.warning("System will continue without SQL Server connectivity")
    except Exception as e:
        logger.error(f"Unexpected error initializing SQL Server: {e}")
        logger.warning("System will continue without SQL Server connectivity")
