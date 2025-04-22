import logging
import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import terraflow, terramap, terrainsight, terraaudit, auth
from app.core.config import settings
from app.db.postgres import init_postgres
from app.db.sqlserver import init_sqlserver
from app.mcp.server import start_mcp_server
from app.messaging.redis_bus import init_redis
from app.utils.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TerraFusion Platform",
    description="A microservices platform for geospatial data processing with AI agent orchestration",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure more restrictively in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(terraflow.router, prefix="/api/etl", tags=["terraflow"])
app.include_router(terramap.router, prefix="/api/tiles", tags=["terramap"])
app.include_router(terrainsight.router, prefix="/api/ai", tags=["terrainsight"])
app.include_router(terraaudit.router, prefix="/api/audit", tags=["terraaudit"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Starting TerraFusion Platform")
    
    # Initialize database connections
    await init_postgres()
    await init_sqlserver()
    
    # Initialize messaging bus
    await init_redis()
    
    # Start MCP server for AI agent orchestration
    await start_mcp_server()
    
    logger.info("TerraFusion Platform started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown"""
    logger.info("Shutting down TerraFusion Platform")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
