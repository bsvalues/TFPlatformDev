import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
from fastapi import BackgroundTasks
import requests

from services.common.database import get_db_session, execute_spatial_query, execute_jcharrispacs_query
from services.common.models import Task, User

# Configure logging
logger = logging.getLogger(__name__)

# MCP server configuration
MCP_SERVER_URL = "http://localhost:8001"  # MCP server URL

# Dictionary to track running agent tasks
running_tasks = {}

# Available agents configuration
AVAILABLE_AGENTS = [
    {
        "id": "spatial_query_agent",
        "name": "Spatial Query Agent",
        "description": "Agent for performing spatial queries and operations on geographic data",
        "capabilities": ["buffer", "intersect", "distance", "area", "point_in_polygon"],
        "parameters": {
            "feature_id": "ID of the feature to analyze",
            "operation": "Spatial operation to perform",
            "distance": "Distance for buffer operations (in meters)",
            "target_feature_id": "Target feature ID for operations involving two features"
        }
    },
    {
        "id": "data_convert_agent",
        "name": "Data Conversion Agent",
        "description": "Agent for converting data between different formats and coordinate systems",
        "capabilities": ["format_conversion", "coordinate_transformation", "schema_mapping"],
        "parameters": {
            "source_data": "Data to convert",
            "source_format": "Format of source data",
            "target_format": "Desired format for converted data",
            "source_crs": "Source coordinate reference system",
            "target_crs": "Target coordinate reference system"
        }
    },
    {
        "id": "audit_agent",
        "name": "Audit Agent",
        "description": "Agent for performing data quality audits and applying corrections",
        "capabilities": ["quality_check", "validation", "error_correction"],
        "parameters": {
            "feature_id": "ID of the feature to audit",
            "rules": "Validation rules to apply",
            "auto_correct": "Whether to automatically apply corrections"
        }
    }
]

def get_available_agents() -> List[Dict[str, Any]]:
    """
    Get list of available AI agents
    
    Returns:
        List of agent configurations
    """
    return AVAILABLE_AGENTS

def run_agent(
    agent_id: str,
    parameters: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> int:
    """
    Run an AI agent with the given parameters
    
    Args:
        agent_id: ID of the agent to run
        parameters: Parameters for the agent
        background_tasks: FastAPI background tasks
        
    Returns:
        Task ID
    """
    # Validate agent ID
    if not any(agent["id"] == agent_id for agent in AVAILABLE_AGENTS):
        raise ValueError(f"Unknown agent ID: {agent_id}")
    
    try:
        with get_db_session() as db:
            # Get user from username
            username = parameters.get("user")
            user = db.query(User).filter(User.username == username).first() if username else None
            
            # Create task record
            task = Task(
                task_type=f"AI_{agent_id}",
                status="pending",
                parameters=parameters,
                user_id=user.id if user else None,
                created_at=datetime.utcnow()
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            # Start task in background
            background_tasks.add_task(execute_agent_task, task.id, agent_id, parameters)
            
            return task.id
    except Exception as e:
        logger.error(f"Error starting agent {agent_id}: {str(e)}")
        raise

def execute_agent_task(task_id: int, agent_id: str, parameters: Dict[str, Any]):
    """
    Execute agent task in background
    
    Args:
        task_id: ID of the task
        agent_id: ID of the agent to run
        parameters: Parameters for the agent
    """
    try:
        with get_db_session() as db:
            # Update task status
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            task.status = "running"
            task.started_at = datetime.utcnow()
            db.commit()
            
            # Keep track of running task
            running_tasks[task_id] = {
                "status": "running",
                "start_time": time.time(),
                "thread": threading.current_thread()
            }
            
            # Execute agent based on ID
            result = None
            if agent_id == "spatial_query_agent":
                result = run_spatial_query_agent(parameters)
            elif agent_id == "data_convert_agent":
                result = run_data_convert_agent(parameters)
            elif agent_id == "audit_agent":
                result = run_audit_agent(parameters)
            else:
                raise ValueError(f"Unknown agent ID: {agent_id}")
            
            # Update task record
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.result = result
            db.commit()
            
            # Remove from running tasks
            if task_id in running_tasks:
                del running_tasks[task_id]
                
    except Exception as e:
        logger.error(f"Error executing agent task {task_id}: {str(e)}")
        try:
            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.completed_at = datetime.utcnow()
                    db.commit()
                
                # Remove from running tasks
                if task_id in running_tasks:
                    del running_tasks[task_id]
        except Exception as inner_e:
            logger.error(f"Error updating failed task status: {str(inner_e)}")

def run_spatial_query_agent(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run spatial query agent to perform spatial operations
    
    Args:
        parameters: Agent parameters
        
    Returns:
        Agent result
    """
    try:
        # Extract parameters
        feature_id = parameters.get("feature_id")
        if not feature_id:
            raise ValueError("feature_id is required")
        
        operation = parameters.get("operation", "buffer")
        target_feature_id = parameters.get("target_feature_id")
        distance = float(parameters.get("distance", 0))
        
        # Get feature geometry
        query = f"""
        SELECT 
            id, 
            feature_id, 
            ST_AsText(geometry) as wkt_geometry
        FROM 
            spatial_features
        WHERE 
            feature_id = '{feature_id}'
        """
        
        result = execute_spatial_query(query)
        
        if result["status"] != "success" or not result["data"]:
            raise ValueError(f"Feature {feature_id} not found")
        
        feature = result["data"][0]
        feature_geom_wkt = feature["wkt_geometry"]
        
        # Perform spatial operation
        if operation == "buffer":
            # Perform buffer operation
            buffer_query = f"""
            SELECT 
                ST_AsGeoJSON(ST_Buffer(
                    ST_GeomFromText('{feature_geom_wkt}', 4326)::geography, 
                    {distance}
                )::geometry) as geometry
            """
            
            buffer_result = execute_spatial_query(buffer_query)
            
            if buffer_result["status"] != "success" or not buffer_result["data"]:
                raise ValueError("Error performing buffer operation")
            
            buffer_geom = json.loads(buffer_result["data"][0]["geometry"])
            
            return {
                "operation": "buffer",
                "feature_id": feature_id,
                "distance": distance,
                "result": {
                    "type": "Feature",
                    "properties": {
                        "operation": "buffer",
                        "source_feature": feature_id,
                        "distance": distance
                    },
                    "geometry": buffer_geom
                }
            }
        
        elif operation == "intersect" and target_feature_id:
            # Get target feature
            target_query = f"""
            SELECT 
                id, 
                feature_id, 
                ST_AsText(geometry) as wkt_geometry
            FROM 
                spatial_features
            WHERE 
                feature_id = '{target_feature_id}'
            """
            
            target_result = execute_spatial_query(target_query)
            
            if target_result["status"] != "success" or not target_result["data"]:
                raise ValueError(f"Target feature {target_feature_id} not found")
            
            target_feature = target_result["data"][0]
            target_geom_wkt = target_feature["wkt_geometry"]
            
            # Perform intersection
            intersect_query = f"""
            SELECT 
                ST_AsGeoJSON(ST_Intersection(
                    ST_GeomFromText('{feature_geom_wkt}', 4326),
                    ST_GeomFromText('{target_geom_wkt}', 4326)
                )) as geometry,
                ST_Area(ST_Intersection(
                    ST_GeomFromText('{feature_geom_wkt}', 4326)::geography,
                    ST_GeomFromText('{target_geom_wkt}', 4326)::geography
                )) as area
            """
            
            intersect_result = execute_spatial_query(intersect_query)
            
            if intersect_result["status"] != "success" or not intersect_result["data"]:
                raise ValueError("Error performing intersection operation")
            
            intersect_geom = json.loads(intersect_result["data"][0]["geometry"]) if intersect_result["data"][0]["geometry"] else None
            intersect_area = intersect_result["data"][0]["area"]
            
            return {
                "operation": "intersect",
                "feature_id": feature_id,
                "target_feature_id": target_feature_id,
                "result": {
                    "type": "Feature",
                    "properties": {
                        "operation": "intersect",
                        "source_feature": feature_id,
                        "target_feature": target_feature_id,
                        "area": intersect_area
                    },
                    "geometry": intersect_geom
                }
            }
        
        elif operation == "distance" and target_feature_id:
            # Get target feature
            target_query = f"""
            SELECT 
                id, 
                feature_id, 
                ST_AsText(geometry) as wkt_geometry
            FROM 
                spatial_features
            WHERE 
                feature_id = '{target_feature_id}'
            """
            
            target_result = execute_spatial_query(target_query)
            
            if target_result["status"] != "success" or not target_result["data"]:
                raise ValueError(f"Target feature {target_feature_id} not found")
            
            target_feature = target_result["data"][0]
            target_geom_wkt = target_feature["wkt_geometry"]
            
            # Calculate distance
            distance_query = f"""
            SELECT 
                ST_Distance(
                    ST_GeomFromText('{feature_geom_wkt}', 4326)::geography,
                    ST_GeomFromText('{target_geom_wkt}', 4326)::geography
                ) as distance
            """
            
            distance_result = execute_spatial_query(distance_query)
            
            if distance_result["status"] != "success" or not distance_result["data"]:
                raise ValueError("Error calculating distance")
            
            calculated_distance = distance_result["data"][0]["distance"]
            
            return {
                "operation": "distance",
                "feature_id": feature_id,
                "target_feature_id": target_feature_id,
                "result": {
                    "distance": calculated_distance,
                    "units": "meters"
                }
            }
        
        elif operation == "area":
            # Calculate area
            area_query = f"""
            SELECT 
                ST_Area(
                    ST_GeomFromText('{feature_geom_wkt}', 4326)::geography
                ) as area
            """
            
            area_result = execute_spatial_query(area_query)
            
            if area_result["status"] != "success" or not area_result["data"]:
                raise ValueError("Error calculating area")
            
            calculated_area = area_result["data"][0]["area"]
            
            return {
                "operation": "area",
                "feature_id": feature_id,
                "result": {
                    "area": calculated_area,
                    "units": "square meters"
                }
            }
        
        else:
            raise ValueError(f"Unsupported operation: {operation}")
            
    except Exception as e:
        logger.error(f"Error in spatial query agent: {str(e)}")
        raise

def run_data_convert_agent(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run data conversion agent to transform data
    
    Args:
        parameters: Agent parameters
        
    Returns:
        Agent result
    """
    try:
        # Extract parameters
        source_format = parameters.get("source_format")
        target_format = parameters.get("target_format")
        source_data = parameters.get("source_data")
        source_crs = parameters.get("source_crs", "EPSG:4326")
        target_crs = parameters.get("target_crs", "EPSG:4326")
        
        if not source_format or not target_format or not source_data:
            raise ValueError("source_format, target_format, and source_data are required")
        
        # Convert based on formats
        if source_format == "wkt" and target_format == "geojson":
            # Convert WKT to GeoJSON
            geojson_query = f"""
            SELECT 
                ST_AsGeoJSON(ST_GeomFromText('{source_data}', {source_crs.split(':')[1]})) as geojson
            """
            
            geojson_result = execute_spatial_query(geojson_query)
            
            if geojson_result["status"] != "success" or not geojson_result["data"]:
                raise ValueError("Error converting WKT to GeoJSON")
            
            geojson = json.loads(geojson_result["data"][0]["geojson"])
            
            return {
                "conversion": "wkt_to_geojson",
                "source_crs": source_crs,
                "target_crs": target_crs,
                "result": geojson
            }
        
        elif source_format == "geojson" and target_format == "wkt":
            # Parse GeoJSON
            if isinstance(source_data, str):
                geojson_data = json.loads(source_data)
            else:
                geojson_data = source_data
                
            geojson_str = json.dumps(geojson_data)
            
            # Convert GeoJSON to WKT
            wkt_query = f"""
            SELECT 
                ST_AsText(ST_GeomFromGeoJSON('{geojson_str}')) as wkt
            """
            
            wkt_result = execute_spatial_query(wkt_query)
            
            if wkt_result["status"] != "success" or not wkt_result["data"]:
                raise ValueError("Error converting GeoJSON to WKT")
            
            wkt = wkt_result["data"][0]["wkt"]
            
            return {
                "conversion": "geojson_to_wkt",
                "source_crs": source_crs,
                "target_crs": target_crs,
                "result": wkt
            }
        
        elif source_format == "coordinates" and target_format == "geojson":
            # Extract coordinates
            if isinstance(source_data, str):
                coords = [float(x.strip()) for x in source_data.split(',')]
            else:
                coords = source_data
                
            if len(coords) < 2:
                raise ValueError("At least two coordinates (x,y) are required")
                
            # Create point GeoJSON
            point_geojson = {
                "type": "Point",
                "coordinates": [coords[0], coords[1]]
            }
            
            return {
                "conversion": "coordinates_to_geojson",
                "source_crs": source_crs,
                "target_crs": target_crs,
                "result": point_geojson
            }
            
        else:
            raise ValueError(f"Unsupported conversion: {source_format} to {target_format}")
            
    except Exception as e:
        logger.error(f"Error in data convert agent: {str(e)}")
        raise

def run_audit_agent(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run audit agent to validate and correct data
    
    Args:
        parameters: Agent parameters
        
    Returns:
        Agent result
    """
    try:
        # Extract parameters
        feature_id = parameters.get("feature_id")
        rules = parameters.get("rules", [])
        auto_correct = parameters.get("auto_correct", False)
        
        if not feature_id:
            raise ValueError("feature_id is required")
        
        # Get feature data
        query = f"""
        SELECT 
            id, 
            feature_id, 
            feature_type,
            properties,
            ST_AsGeoJSON(geometry) as geometry,
            source_system,
            is_synced
        FROM 
            spatial_features
        WHERE 
            feature_id = '{feature_id}'
        """
        
        result = execute_spatial_query(query)
        
        if result["status"] != "success" or not result["data"]:
            raise ValueError(f"Feature {feature_id} not found")
        
        feature = result["data"][0]
        feature_geom = json.loads(feature["geometry"])
        properties = feature["properties"] or {}
        
        # Perform validation checks
        validation_results = []
        corrections = []
        
        # Check for geometries with self-intersections
        if "valid_geometry" in rules or not rules:
            valid_query = f"""
            SELECT 
                ST_IsValid(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}')) as is_valid,
                ST_IsValidReason(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}')) as reason
            """
            
            valid_result = execute_spatial_query(valid_query)
            
            if valid_result["status"] == "success" and valid_result["data"]:
                is_valid = valid_result["data"][0]["is_valid"]
                reason = valid_result["data"][0]["reason"]
                
                validation_results.append({
                    "rule": "valid_geometry",
                    "passed": is_valid,
                    "message": reason if not is_valid else "Geometry is valid"
                })
                
                # Auto-correct if requested
                if not is_valid and auto_correct:
                    fix_query = f"""
                    SELECT 
                        ST_AsGeoJSON(ST_MakeValid(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}'))) as fixed_geometry
                    """
                    
                    fix_result = execute_spatial_query(fix_query)
                    
                    if fix_result["status"] == "success" and fix_result["data"] and fix_result["data"][0]["fixed_geometry"]:
                        fixed_geom = json.loads(fix_result["data"][0]["fixed_geometry"])
                        
                        corrections.append({
                            "rule": "valid_geometry",
                            "original": feature_geom,
                            "corrected": fixed_geom,
                            "applied": auto_correct
                        })
                        
                        # Update feature if auto_correct is true
                        if auto_correct:
                            update_query = f"""
                            UPDATE spatial_features
                            SET geometry = ST_GeomFromGeoJSON('{json.dumps(fixed_geom)}')
                            WHERE feature_id = '{feature_id}'
                            """
                            
                            execute_spatial_query(update_query)
        
        # Check for required properties
        if "required_properties" in rules or not rules:
            required_fields = parameters.get("required_fields", [])
            missing_fields = []
            
            for field in required_fields:
                if field not in properties:
                    missing_fields.append(field)
            
            validation_results.append({
                "rule": "required_properties",
                "passed": len(missing_fields) == 0,
                "message": f"Missing required fields: {', '.join(missing_fields)}" if missing_fields else "All required fields present"
            })
        
        # Check for coordinates within expected bounds
        if "coordinate_bounds" in rules or not rules:
            bounds = parameters.get("bounds", [-180, -90, 180, 90])  # [min_x, min_y, max_x, max_y]
            
            bounds_query = f"""
            SELECT 
                ST_XMin(ST_Envelope(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}'))) as min_x,
                ST_YMin(ST_Envelope(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}'))) as min_y,
                ST_XMax(ST_Envelope(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}'))) as max_x,
                ST_YMax(ST_Envelope(ST_GeomFromGeoJSON('{json.dumps(feature_geom)}'))) as max_y
            """
            
            bounds_result = execute_spatial_query(bounds_query)
            
            if bounds_result["status"] == "success" and bounds_result["data"]:
                feature_bounds = [
                    bounds_result["data"][0]["min_x"],
                    bounds_result["data"][0]["min_y"],
                    bounds_result["data"][0]["max_x"],
                    bounds_result["data"][0]["max_y"]
                ]
                
                is_within_bounds = (
                    feature_bounds[0] >= bounds[0] and
                    feature_bounds[1] >= bounds[1] and
                    feature_bounds[2] <= bounds[2] and
                    feature_bounds[3] <= bounds[3]
                )
                
                validation_results.append({
                    "rule": "coordinate_bounds",
                    "passed": is_within_bounds,
                    "message": "Coordinates out of bounds" if not is_within_bounds else "Coordinates within bounds",
                    "feature_bounds": feature_bounds,
                    "expected_bounds": bounds
                })
        
        return {
            "feature_id": feature_id,
            "validation_results": validation_results,
            "corrections": corrections,
            "summary": {
                "total_checks": len(validation_results),
                "passed": sum(1 for result in validation_results if result["passed"]),
                "failed": sum(1 for result in validation_results if not result["passed"]),
                "corrections_applied": len([c for c in corrections if c["applied"]])
            }
        }
            
    except Exception as e:
        logger.error(f"Error in audit agent: {str(e)}")
        raise

def get_agent_result(task_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the result of an agent task
    
    Args:
        task_id: ID of the task
        
    Returns:
        Task result
    """
    try:
        with get_db_session() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None
            
            # Get user information
            user = db.query(User).filter(User.id == task.user_id).first() if task.user_id else None
            
            result = {
                "id": task.id,
                "type": task.task_type,
                "status": task.status,
                "parameters": task.parameters,
                "result": task.result,
                "error_message": task.error_message,
                "user": user.username if user else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None
            }
            
            # Add runtime info if job is still running
            if task_id in running_tasks:
                elapsed_time = time.time() - running_tasks[task_id]["start_time"]
                result["elapsed_seconds"] = elapsed_time
            
            return result
    except Exception as e:
        logger.error(f"Error getting agent result: {str(e)}")
        raise
