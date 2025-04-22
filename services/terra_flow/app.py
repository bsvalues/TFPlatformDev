import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import uvicorn

from services.common.auth import get_current_user, has_role
from services.terra_flow.etl import (
    start_etl_job, 
    get_etl_job_status,
    get_etl_job_list,
    cancel_etl_job
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="TerraFlow Service",
    description="ETL and data flow service for TerraFusion platform",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terra_flow"}

@app.post("/etl/jobs", response_model=Dict[str, Any])
async def create_etl_job(
    job_spec: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Start a new ETL job
    
    Job specification should include:
    - source: Source system (e.g., "jcharrispacs", "shapefile")
    - target: Target system (e.g., "postgresql", "geojson")
    - source_params: Parameters for the source system
    - target_params: Parameters for the target system
    - transformation: Optional transformation steps
    """
    try:
        # Validate job specification
        if "source" not in job_spec or "target" not in job_spec:
            raise HTTPException(status_code=400, detail="Job specification must include source and target")
        
        # Start ETL job in background
        job_id = start_etl_job(
            job_spec, 
            current_user["sub"],
            background_tasks
        )
        
        return {
            "status": "success",
            "job_id": job_id,
            "message": "ETL job started successfully"
        }
    except Exception as e:
        logger.error(f"Error starting ETL job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting ETL job: {str(e)}")

@app.get("/etl/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job_status(
    job_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the status of an ETL job
    """
    try:
        job_status = get_etl_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="ETL job not found")
        
        return {
            "status": "success",
            "job": job_status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ETL job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting ETL job status: {str(e)}")

@app.get("/etl/jobs", response_model=Dict[str, Any])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 10, 
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List ETL jobs with optional filtering by status
    """
    try:
        jobs = get_etl_job_list(status, limit, offset)
        
        return {
            "status": "success",
            "jobs": jobs,
            "total": len(jobs),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error listing ETL jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing ETL jobs: {str(e)}")

@app.delete("/etl/jobs/{job_id}", response_model=Dict[str, Any])
async def cancel_job(
    job_id: int,
    current_user: Dict[str, Any] = Depends(has_role(["admin", "etl_manager"]))
):
    """
    Cancel an ETL job (requires admin or etl_manager role)
    """
    try:
        result = cancel_etl_job(job_id)
        if not result:
            raise HTTPException(status_code=404, detail="ETL job not found or already completed")
        
        return {
            "status": "success",
            "message": f"ETL job {job_id} cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling ETL job: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cancelling ETL job: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
