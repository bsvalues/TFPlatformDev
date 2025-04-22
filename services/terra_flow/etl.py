import os
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import threading
import pandas as pd
import geopandas as gpd
from shapely import wkt
from fastapi import BackgroundTasks
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.common.database import get_db_session, execute_jcharrispacs_query, execute_spatial_query
from services.common.models import Task, SpatialFeature, SyncRecord, User

# Configure logging
logger = logging.getLogger(__name__)

# Dictionary to track running ETL jobs
running_jobs = {}

def start_etl_job(
    job_spec: Dict[str, Any], 
    username: str,
    background_tasks: BackgroundTasks
) -> int:
    """
    Start an ETL job with the given specification
    
    Args:
        job_spec: ETL job specification
        username: Username of the initiator
        background_tasks: FastAPI background tasks
        
    Returns:
        job_id: ID of the created job
    """
    try:
        with get_db_session() as db:
            # Get user ID
            user = db.query(User).filter(User.username == username).first()
            user_id = user.id if user else None
            
            # Create task record
            task = Task(
                task_type="ETL",
                status="pending",
                parameters=job_spec,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            # Start task in background
            background_tasks.add_task(execute_etl_job, task.id, job_spec)
            
            return task.id
    except Exception as e:
        logger.error(f"Error starting ETL job: {str(e)}")
        raise

def execute_etl_job(job_id: int, job_spec: Dict[str, Any]):
    """
    Execute ETL job in background
    
    Args:
        job_id: ID of the job to execute
        job_spec: ETL job specification
    """
    try:
        with get_db_session() as db:
            # Update task status
            task = db.query(Task).filter(Task.id == job_id).first()
            if not task:
                logger.error(f"Task {job_id} not found")
                return
            
            task.status = "running"
            task.started_at = datetime.utcnow()
            db.commit()
            
            # Keep track of running job
            running_jobs[job_id] = {
                "status": "running",
                "start_time": time.time(),
                "thread": threading.current_thread()
            }
            
            # Execute ETL based on source and target
            source = job_spec.get("source")
            target = job_spec.get("target")
            source_params = job_spec.get("source_params", {})
            target_params = job_spec.get("target_params", {})
            transform_params = job_spec.get("transformation", {})
            
            # Load data from source
            data = None
            if source == "jcharrispacs":
                data = extract_from_jcharrispacs(source_params)
            elif source == "shapefile":
                data = extract_from_shapefile(source_params)
            elif source == "geojson":
                data = extract_from_geojson(source_params)
            else:
                raise ValueError(f"Unsupported source: {source}")
            
            # Apply transformations
            if transform_params:
                data = transform_data(data, transform_params)
            
            # Load data to target
            result = None
            if target == "postgresql":
                result = load_to_postgresql(data, target_params)
            elif target == "geojson":
                result = load_to_geojson(data, target_params)
            else:
                raise ValueError(f"Unsupported target: {target}")
            
            # Update task record
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.result = result
            db.commit()
            
            # Create sync records if needed
            if source == "jcharrispacs" and target == "postgresql":
                create_sync_records(db, data, result, "inbound", source, target)
            
            # Remove from running jobs
            if job_id in running_jobs:
                del running_jobs[job_id]
                
    except Exception as e:
        logger.error(f"Error executing ETL job {job_id}: {str(e)}")
        try:
            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == job_id).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.completed_at = datetime.utcnow()
                    db.commit()
                
                # Remove from running jobs
                if job_id in running_jobs:
                    del running_jobs[job_id]
        except Exception as inner_e:
            logger.error(f"Error updating failed task status: {str(inner_e)}")

def extract_from_jcharrispacs(params: Dict[str, Any]) -> gpd.GeoDataFrame:
    """
    Extract data from JCHARRISPACS SQL Server
    
    Args:
        params: Extraction parameters including SQL query
        
    Returns:
        GeoDataFrame containing the extracted data
    """
    query = params.get("query")
    if not query:
        raise ValueError("SQL query is required for JCHARRISPACS extraction")
    
    # Execute query against SQL Server
    result = execute_jcharrispacs_query(query)
    
    if result.get("status") != "success" or not result.get("data"):
        raise ValueError(f"Error executing JCHARRISPACS query: {result.get('message')}")
    
    # Convert to DataFrame
    df = pd.DataFrame(result.get("data"))
    
    # Convert to GeoDataFrame if geometry column exists
    geom_column = params.get("geometry_column", "geometry")
    if geom_column in df.columns:
        df[geom_column] = df[geom_column].apply(lambda x: wkt.loads(x) if x else None)
        gdf = gpd.GeoDataFrame(df, geometry=geom_column, crs="EPSG:4326")
    else:
        # Create empty GeoDataFrame
        gdf = gpd.GeoDataFrame(df)
    
    return gdf

def extract_from_shapefile(params: Dict[str, Any]) -> gpd.GeoDataFrame:
    """
    Extract data from a shapefile
    
    Args:
        params: Extraction parameters including file path
        
    Returns:
        GeoDataFrame containing the extracted data
    """
    file_path = params.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise ValueError(f"Invalid shapefile path: {file_path}")
    
    # Read shapefile
    gdf = gpd.read_file(file_path)
    
    # Ensure CRS is EPSG:4326 (WGS84)
    if gdf.crs and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    return gdf

def extract_from_geojson(params: Dict[str, Any]) -> gpd.GeoDataFrame:
    """
    Extract data from a GeoJSON file or string
    
    Args:
        params: Extraction parameters including file path or GeoJSON string
        
    Returns:
        GeoDataFrame containing the extracted data
    """
    file_path = params.get("file_path")
    geojson_str = params.get("geojson")
    
    if file_path and os.path.exists(file_path):
        # Read from file
        gdf = gpd.read_file(file_path)
    elif geojson_str:
        # Parse from string
        geojson_data = json.loads(geojson_str)
        gdf = gpd.GeoDataFrame.from_features(geojson_data["features"] if "features" in geojson_data else geojson_data)
    else:
        raise ValueError("Valid file path or GeoJSON string is required")
    
    # Ensure CRS is EPSG:4326 (WGS84)
    if gdf.crs and gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")
    
    return gdf

def transform_data(data: gpd.GeoDataFrame, transform_params: Dict[str, Any]) -> gpd.GeoDataFrame:
    """
    Apply transformations to the data
    
    Args:
        data: GeoDataFrame to transform
        transform_params: Transformation parameters
        
    Returns:
        Transformed GeoDataFrame
    """
    result = data.copy()
    
    # Apply field mappings
    field_mappings = transform_params.get("field_mappings", {})
    if field_mappings:
        for target_field, source_field in field_mappings.items():
            if source_field in result.columns:
                result[target_field] = result[source_field]
    
    # Apply field calculations
    field_calculations = transform_params.get("field_calculations", {})
    for field, expression in field_calculations.items():
        # DANGER: eval can be dangerous, only use with trusted expressions
        # In production, use a safer expression parser
        result[field] = result.apply(lambda row: eval(expression, {"row": row, "pd": pd}), axis=1)
    
    # Apply spatial transformations
    spatial_transforms = transform_params.get("spatial_transforms", [])
    for transform in spatial_transforms:
        transform_type = transform.get("type")
        
        if transform_type == "buffer":
            distance = transform.get("distance", 0)
            result["geometry"] = result.geometry.buffer(distance)
        
        elif transform_type == "simplify":
            tolerance = transform.get("tolerance", 0.001)
            result["geometry"] = result.geometry.simplify(tolerance)
            
        elif transform_type == "centroid":
            result["geometry"] = result.geometry.centroid
    
    return result

def load_to_postgresql(data: gpd.GeoDataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load data to PostgreSQL/PostGIS
    
    Args:
        data: GeoDataFrame to load
        params: Load parameters
        
    Returns:
        Result information
    """
    table_name = params.get("table_name")
    if not table_name:
        raise ValueError("Table name is required for PostgreSQL loading")
    
    schema = params.get("schema", "public")
    if_exists = params.get("if_exists", "append")  # append, replace, fail
    
    try:
        with get_db_session() as db:
            # Check if we're writing to spatial_features table
            if table_name == "spatial_features":
                # Insert records one by one to use the SpatialFeature model
                inserted_features = []
                for _, row in data.iterrows():
                    properties = {col: row[col] for col in data.columns if col != "geometry"}
                    
                    # Create feature ID if not present
                    feature_id = properties.get("feature_id") or properties.get("id") or f"feature_{len(inserted_features)}"
                    feature_type = properties.get("feature_type") or "unknown"
                    source_system = properties.get("source_system") or params.get("source_system", "unknown")
                    
                    # Remove these from properties to avoid duplication
                    for key in ["feature_id", "id", "feature_type", "source_system"]:
                        if key in properties:
                            del properties[key]
                    
                    # Create SpatialFeature
                    feature = SpatialFeature(
                        feature_id=str(feature_id),
                        feature_type=feature_type,
                        properties=properties,
                        geometry=f"SRID=4326;{row.geometry.wkt}",
                        source_system=source_system,
                        is_synced=True
                    )
                    db.add(feature)
                    inserted_features.append(feature_id)
                
                db.commit()
                return {
                    "table": f"{schema}.{table_name}",
                    "inserted": len(inserted_features),
                    "features": inserted_features
                }
            else:
                # Use GeoPandas to_postgis for other tables
                if hasattr(data, "to_postgis"):
                    data.to_postgis(
                        table_name,
                        db.bind,
                        schema=schema,
                        if_exists=if_exists,
                        index=False
                    )
                else:
                    # Fallback to pandas to_sql for non-spatial data
                    data.to_sql(
                        table_name,
                        db.bind,
                        schema=schema,
                        if_exists=if_exists,
                        index=False
                    )
                
                return {
                    "table": f"{schema}.{table_name}",
                    "inserted": len(data)
                }
    except Exception as e:
        logger.error(f"Error loading to PostgreSQL: {str(e)}")
        raise

def load_to_geojson(data: gpd.GeoDataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load data to GeoJSON file
    
    Args:
        data: GeoDataFrame to load
        params: Load parameters
        
    Returns:
        Result information
    """
    file_path = params.get("file_path")
    if not file_path:
        raise ValueError("File path is required for GeoJSON loading")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    
    # Convert to GeoJSON and save
    geojson_data = json.loads(data.to_json())
    
    with open(file_path, 'w') as f:
        json.dump(geojson_data, f)
    
    return {
        "file": file_path,
        "features": len(data)
    }

def create_sync_records(
    db: Session,
    data: gpd.GeoDataFrame,
    result: Dict[str, Any],
    sync_direction: str,
    source_system: str,
    target_system: str
):
    """
    Create sync records for tracking data synchronization
    
    Args:
        db: Database session
        data: Source data
        result: Load result
        sync_direction: Direction of sync (inbound or outbound)
        source_system: Source system name
        target_system: Target system name
    """
    for feature_id in result.get("features", []):
        # Get the feature
        feature = db.query(SpatialFeature).filter(SpatialFeature.feature_id == feature_id).first()
        if not feature:
            continue
        
        # Create sync record
        sync_record = SyncRecord(
            source_system=source_system,
            entity_type="SpatialFeature",
            entity_id=feature.id,
            target_id=None,  # External ID if available
            sync_direction=sync_direction,
            sync_status="completed",
            sync_timestamp=datetime.utcnow()
        )
        db.add(sync_record)
    
    db.commit()

def get_etl_job_status(job_id: int) -> Optional[Dict[str, Any]]:
    """
    Get the status of an ETL job
    
    Args:
        job_id: ID of the job
        
    Returns:
        Job status information
    """
    try:
        with get_db_session() as db:
            task = db.query(Task).filter(Task.id == job_id).first()
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
            if job_id in running_jobs:
                elapsed_time = time.time() - running_jobs[job_id]["start_time"]
                result["elapsed_seconds"] = elapsed_time
            
            return result
    except Exception as e:
        logger.error(f"Error getting ETL job status: {str(e)}")
        raise

def get_etl_job_list(
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get a list of ETL jobs
    
    Args:
        status: Filter by job status
        limit: Maximum number of jobs to return
        offset: Offset for pagination
        
    Returns:
        List of job information
    """
    try:
        with get_db_session() as db:
            query = db.query(Task).filter(Task.task_type == "ETL")
            
            if status:
                query = query.filter(Task.status == status)
            
            tasks = query.order_by(Task.created_at.desc()).limit(limit).offset(offset).all()
            
            result = []
            for task in tasks:
                user = db.query(User).filter(User.id == task.user_id).first() if task.user_id else None
                
                task_info = {
                    "id": task.id,
                    "status": task.status,
                    "parameters": task.parameters,
                    "user": user.username if user else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "created_at": task.created_at.isoformat() if task.created_at else None
                }
                
                # Add runtime info if job is still running
                if task.id in running_jobs:
                    elapsed_time = time.time() - running_jobs[task.id]["start_time"]
                    task_info["elapsed_seconds"] = elapsed_time
                
                result.append(task_info)
            
            return result
    except Exception as e:
        logger.error(f"Error listing ETL jobs: {str(e)}")
        raise

def cancel_etl_job(job_id: int) -> bool:
    """
    Cancel an ETL job
    
    Args:
        job_id: ID of the job to cancel
        
    Returns:
        True if job was cancelled, False otherwise
    """
    try:
        # Check if job is running
        if job_id not in running_jobs:
            # Check if job exists but is not running
            with get_db_session() as db:
                task = db.query(Task).filter(Task.id == job_id).first()
                if not task or task.status not in ["pending", "running"]:
                    return False
                
                # Update task status
                task.status = "cancelled"
                task.completed_at = datetime.utcnow()
                task.error_message = "Job cancelled by user"
                db.commit()
                
                return True
        
        # Job is running, try to cancel the thread
        # Note: This is a simplified approach and may not work in all cases
        # In production, you might need a more robust task cancellation mechanism
        running_job = running_jobs[job_id]
        thread = running_job.get("thread")
        
        # Mark job as cancelled
        running_job["status"] = "cancelled"
        
        # Update database record
        with get_db_session() as db:
            task = db.query(Task).filter(Task.id == job_id).first()
            if task:
                task.status = "cancelled"
                task.completed_at = datetime.utcnow()
                task.error_message = "Job cancelled by user"
                db.commit()
        
        # Remove from running jobs
        if job_id in running_jobs:
            del running_jobs[job_id]
        
        return True
    except Exception as e:
        logger.error(f"Error cancelling ETL job: {str(e)}")
        return False
