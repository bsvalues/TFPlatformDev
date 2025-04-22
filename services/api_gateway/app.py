import os
import logging
import httpx
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="TerraFusion API Gateway",
    description="API Gateway for the TerraFusion platform microservices",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service configurations
SERVICE_CONFIG = {
    "terra_flow": {
        "url": "http://localhost:8000",
        "prefix": "/etl"
    },
    "terra_map": {
        "url": "http://localhost:8000",
        "prefix": "/map"
    },
    "terra_insight": {
        "url": "http://localhost:8000",
        "prefix": "/ai"
    },
    "terra_audit": {
        "url": "http://localhost:8000",
        "prefix": "/audit"
    },
    "mcp": {
        "url": "http://localhost:8001",
        "prefix": "/mcp"
    }
}

# HTTP client
http_client = httpx.AsyncClient(timeout=30.0)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await http_client.aclose()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api_gateway"}

@app.get("/services")
async def list_services():
    """
    List available services
    """
    return {
        "status": "success",
        "services": list(SERVICE_CONFIG.keys())
    }

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_service(service: str, path: str, request: Request):
    """
    Proxy requests to the appropriate service
    
    Args:
        service: Service name
        path: Request path
        request: FastAPI request object
    """
    # Check if service exists
    if service not in SERVICE_CONFIG:
        raise HTTPException(status_code=404, detail=f"Service {service} not found")
    
    # Get service configuration
    service_config = SERVICE_CONFIG[service]
    
    # Build target URL
    target_url = f"{service_config['url']}{path}"
    
    try:
        # Get request body if any
        body = await request.body()
        
        # Forward request to target service
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=body,
            follow_redirects=True
        )
        
        # Return response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Error proxying request to {target_url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error proxying request: {str(e)}")

@app.get("/etl/{path:path}")
async def proxy_terra_flow(path: str, request: Request):
    """
    Proxy requests to TerraFlow service
    
    Args:
        path: Request path
        request: FastAPI request object
    """
    return await proxy_service("terra_flow", f"/{path}", request)

@app.get("/map/{path:path}")
async def proxy_terra_map(path: str, request: Request):
    """
    Proxy requests to TerraMap service
    
    Args:
        path: Request path
        request: FastAPI request object
    """
    return await proxy_service("terra_map", f"/{path}", request)

@app.get("/ai/{path:path}")
async def proxy_terra_insight(path: str, request: Request):
    """
    Proxy requests to TerraInsight service
    
    Args:
        path: Request path
        request: FastAPI request object
    """
    return await proxy_service("terra_insight", f"/{path}", request)

@app.get("/audit/{path:path}")
async def proxy_terra_audit(path: str, request: Request):
    """
    Proxy requests to TerraAudit service
    
    Args:
        path: Request path
        request: FastAPI request object
    """
    return await proxy_service("terra_audit", f"/{path}", request)

@app.get("/mcp/{path:path}")
async def proxy_mcp(path: str, request: Request):
    """
    Proxy requests to MCP service
    
    Args:
        path: Request path
        request: FastAPI request object
    """
    return await proxy_service("mcp", f"/{path}", request)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
