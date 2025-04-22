import os
import secrets
from typing import Any, Dict, List, Optional

from pydantic import BaseSettings, PostgresDsn, validator


class Settings(BaseSettings):
    # API configurations
    API_V1_STR: str = "/api"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS settings
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # PostgreSQL/PostGIS database
    POSTGRES_SERVER: str = os.environ.get("PGHOST", "localhost")
    POSTGRES_PORT: str = os.environ.get("PGPORT", "5432")
    POSTGRES_USER: str = os.environ.get("PGUSER", "postgres")
    POSTGRES_PASSWORD: str = os.environ.get("PGPASSWORD", "")
    POSTGRES_DB: str = os.environ.get("PGDATABASE", "terrafusion")
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    # SQL Server (JCHARRISPACS) connection
    SQLSERVER_CONN_STRING: str = os.environ.get("JCHARRISPACS_CONN", "")
    
    # Redis configuration
    REDIS_HOST: str = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.environ.get("REDIS_PORT", "6379"))
    
    # MCP Server configuration
    MCP_SERVER_PORT: int = int(os.environ.get("MCP_SERVER_PORT", "8001"))
    MCP_API_KEY: str = os.environ.get("MCP_API_KEY", secrets.token_hex(16))

    # Active Directory authentication settings
    AD_SERVER: str = os.environ.get("AD_SERVER", "")
    AD_DOMAIN: str = os.environ.get("AD_DOMAIN", "")
    AD_BASE_DN: str = os.environ.get("AD_BASE_DN", "")
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_postgres_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        
        # Use the DATABASE_URL environment variable if provided
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            return db_url
            
        # Otherwise, construct the DB URL from individual components
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )


settings = Settings()
