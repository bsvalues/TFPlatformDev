from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models.user import User
from app.db.postgres import get_db
from app.mcp.agents.spatial_query_agent import SpatialQueryAgent
from app.mcp.tools.postgis_tools import PostGISTools

router = APIRouter()

@router.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_spatial_data(
    analysis_type: str = Query(..., description="Type of spatial analysis"),
    geometry: str = Query(..., description="WKT geometry for analysis"),
    distance: Optional[float] = Query(None, description="Distance in meters for buffer operations"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze spatial data using AI tools
    """
    try:
        # Initialize tools
        postgis_tools = PostGISTools(db)
        
        # Initialize agent
        spatial_agent = SpatialQueryAgent(postgis_tools=postgis_tools)
        
        # Execute analysis based on type
        if analysis_type == "buffer":
            if not distance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Distance parameter is required for buffer analysis"
                )
                
            result = await spatial_agent.execute_buffer_analysis(geometry, distance)
            return {
                "analysis_type": analysis_type,
                "result": result,
                "parameters": {
                    "geometry": geometry,
                    "distance": distance
                }
            }
            
        elif analysis_type == "intersection":
            target_layer = Query(..., description="Target layer to intersect with")
            result = await spatial_agent.execute_intersection_analysis(geometry, target_layer)
            return {
                "analysis_type": analysis_type,
                "result": result,
                "parameters": {
                    "geometry": geometry,
                    "target_layer": target_layer
                }
            }
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported analysis type: {analysis_type}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing spatial data: {str(e)}"
        )


@router.post("/query", status_code=status.HTTP_200_OK)
async def natural_language_query(
    query: str = Query(..., description="Natural language query for spatial data"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Execute natural language queries using AI agents
    """
    try:
        # Initialize tools
        postgis_tools = PostGISTools(db)
        
        # Initialize agent
        spatial_agent = SpatialQueryAgent(postgis_tools=postgis_tools)
        
        # Process natural language query
        result = await spatial_agent.process_natural_language_query(query)
        
        return {
            "query": query,
            "result": result,
            "sql_generated": result.get("sql", "No SQL generated"),
            "explanation": result.get("explanation", "")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing natural language query: {str(e)}"
        )


@router.get("/agents", status_code=status.HTTP_200_OK)
async def list_available_agents(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List available AI agents for spatial analysis
    """
    try:
        # For demonstration, return a static list of agents
        # In production, this would be dynamically generated based on registered agents
        return [
            {
                "id": "spatial-query-agent",
                "name": "Spatial Query Agent",
                "description": "Executes spatial queries and analysis operations",
                "capabilities": ["buffer", "intersection", "natural-language-query"]
            },
            {
                "id": "data-convert-agent",
                "name": "Data Conversion Agent",
                "description": "Converts between different geospatial data formats",
                "capabilities": ["format-conversion", "coordinate-transformation"]
            },
            {
                "id": "audit-agent",
                "name": "Audit Agent",
                "description": "Audits and corrects geospatial data",
                "capabilities": ["data-validation", "correction-suggestions"]
            }
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing available agents: {str(e)}"
        )


@router.post("/agents/{agent_id}/execute", status_code=status.HTTP_200_OK)
async def execute_agent(
    agent_id: str = Path(..., description="ID of the agent to execute"),
    operation: str = Query(..., description="Operation to execute"),
    parameters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Execute a specific AI agent operation
    """
    try:
        # Initialize appropriate agent based on agent_id
        if agent_id == "spatial-query-agent":
            postgis_tools = PostGISTools(db)
            agent = SpatialQueryAgent(postgis_tools=postgis_tools)
            
            # Execute requested operation
            if operation == "buffer":
                geometry = parameters.get("geometry")
                distance = parameters.get("distance")
                
                if not geometry or not distance:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing required parameters: geometry and distance"
                    )
                    
                result = await agent.execute_buffer_analysis(geometry, distance)
                return {
                    "agent_id": agent_id,
                    "operation": operation,
                    "result": result
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported operation '{operation}' for agent '{agent_id}'"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent '{agent_id}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing agent operation: {str(e)}"
        )
