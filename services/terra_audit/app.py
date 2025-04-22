import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import uvicorn

from services.common.auth import get_current_user, has_role
from services.terra_audit.audit import (
    create_audit_log, 
    get_audit_log, 
    search_audit_logs,
    get_changes_by_feature
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="TerraAudit Service",
    description="Audit logging and compliance service for TerraFusion platform",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terra_audit"}

@app.post("/logs", response_model=Dict[str, Any])
async def create_log(
    log_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new audit log entry
    
    Log data should include:
    - action: The action performed (create, update, delete, etc.)
    - entity_type: Type of entity affected
    - entity_id: ID of the entity affected
    - before_state: State before the change (optional)
    - after_state: State after the change (optional)
    """
    try:
        # Add user and IP information
        log_data["user_id"] = current_user["sub"]
        
        # Create audit log
        log_id = create_audit_log(log_data)
        
        return {
            "status": "success",
            "log_id": log_id,
            "message": "Audit log created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating audit log: {str(e)}")

@app.get("/logs/{log_id}", response_model=Dict[str, Any])
async def get_log(
    log_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get details of a specific audit log entry
    """
    try:
        log = get_audit_log(log_id)
        
        if not log:
            raise HTTPException(status_code=404, detail="Audit log not found")
        
        return {
            "status": "success",
            "log": log
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting audit log: {str(e)}")

@app.get("/logs", response_model=Dict[str, Any])
async def search_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Search audit logs with filters
    """
    try:
        logs = search_audit_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        return {
            "status": "success",
            "logs": logs,
            "total": len(logs),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error searching audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching audit logs: {str(e)}")

@app.get("/features/{feature_id}/history", response_model=Dict[str, Any])
async def feature_history(
    feature_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get change history for a specific feature
    """
    try:
        changes = get_changes_by_feature(feature_id, limit, offset)
        
        return {
            "status": "success",
            "feature_id": feature_id,
            "changes": changes,
            "total": len(changes),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting feature history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feature history: {str(e)}")

@app.get("/reports/activity", response_model=Dict[str, Any])
async def activity_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    group_by: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(has_role(["admin", "auditor"]))
):
    """
    Generate activity report (requires admin or auditor role)
    
    Group by options: user, action, entity_type, day, week, month
    """
    try:
        # Group by validation
        valid_group_by = ["user", "action", "entity_type", "day", "week", "month"]
        if group_by and group_by not in valid_group_by:
            raise HTTPException(status_code=400, detail=f"Invalid group_by value. Valid options: {', '.join(valid_group_by)}")
        
        # Build SQL query based on parameters
        query = """
        SELECT 
        """
        
        if group_by == "user":
            query += "u.username as group_key, COUNT(*) as count"
        elif group_by == "action":
            query += "a.action as group_key, COUNT(*) as count"
        elif group_by == "entity_type":
            query += "a.entity_type as group_key, COUNT(*) as count"
        elif group_by == "day":
            query += "DATE(a.timestamp) as group_key, COUNT(*) as count"
        elif group_by == "week":
            query += "DATE_TRUNC('week', a.timestamp) as group_key, COUNT(*) as count"
        elif group_by == "month":
            query += "DATE_TRUNC('month', a.timestamp) as group_key, COUNT(*) as count"
        else:
            query += "COUNT(*) as count"
        
        query += """
        FROM 
            audit_logs a
        LEFT JOIN
            users u ON a.user_id = u.id
        WHERE 
            1=1
        """
        
        params = {}
        
        if start_date:
            query += " AND a.timestamp >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND a.timestamp <= :end_date"
            params["end_date"] = end_date
        
        if group_by:
            query += " GROUP BY group_key ORDER BY count DESC"
        
        # Execute query
        from services.common.database import execute_spatial_query
        result = execute_spatial_query(query, params)
        
        if result["status"] != "success":
            raise Exception(f"Error executing report query: {result.get('message')}")
        
        return {
            "status": "success",
            "report": {
                "type": "activity",
                "start_date": start_date,
                "end_date": end_date,
                "group_by": group_by,
                "data": result["data"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating activity report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating activity report: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
