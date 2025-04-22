import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import uvicorn

from services.common.auth import get_current_user, has_role
from services.terra_insight.ai import (
    run_agent, 
    get_agent_result,
    get_available_agents
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="TerraInsight Service",
    description="AI and analytics service for TerraFusion platform",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terra_insight"}

@app.get("/agents", response_model=Dict[str, Any])
async def list_agents(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get list of available AI agents
    """
    try:
        agents = get_available_agents()
        
        return {
            "status": "success",
            "agents": agents
        }
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing agents: {str(e)}")

@app.post("/agents/{agent_id}/run", response_model=Dict[str, Any])
async def run_agent_endpoint(
    agent_id: str,
    parameters: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Run an AI agent with the given parameters
    
    Args:
        agent_id: ID of the agent to run
        parameters: Parameters for the agent
        background_tasks: FastAPI background tasks
    """
    try:
        # Add user information to parameters
        parameters["user"] = current_user["sub"]
        
        # Run agent in background
        task_id = run_agent(agent_id, parameters, background_tasks)
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": f"Agent {agent_id} started successfully"
        }
    except Exception as e:
        logger.error(f"Error running agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running agent: {str(e)}")

@app.get("/agents/tasks/{task_id}", response_model=Dict[str, Any])
async def get_agent_result_endpoint(
    task_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the result of an agent task
    
    Args:
        task_id: ID of the task
    """
    try:
        result = get_agent_result(task_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "status": "success",
            "task": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent result: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting agent result: {str(e)}")

@app.post("/spatial/analysis", response_model=Dict[str, Any])
async def spatial_analysis(
    analysis_type: str,
    parameters: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Run a spatial analysis
    
    Args:
        analysis_type: Type of analysis to run
        parameters: Parameters for the analysis
        background_tasks: FastAPI background tasks
    """
    try:
        # Map analysis type to agent
        agent_mapping = {
            "buffer": "spatial_query_agent",
            "intersection": "spatial_query_agent",
            "distance": "spatial_query_agent",
            "area": "spatial_query_agent",
            "convert": "data_convert_agent"
        }
        
        if analysis_type not in agent_mapping:
            raise HTTPException(status_code=400, detail=f"Unsupported analysis type: {analysis_type}")
        
        # Add analysis type to parameters
        parameters["analysis_type"] = analysis_type
        parameters["user"] = current_user["sub"]
        
        # Run the appropriate agent
        agent_id = agent_mapping[analysis_type]
        task_id = run_agent(agent_id, parameters, background_tasks)
        
        return {
            "status": "success",
            "task_id": task_id,
            "message": f"Spatial analysis {analysis_type} started successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running spatial analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running spatial analysis: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
