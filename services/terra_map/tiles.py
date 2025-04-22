import json
import logging
import math
from typing import Dict, Any, List, Optional, Tuple
import mercantile
from shapely.geometry import box
from services.common.database import execute_spatial_query
from services.common.models import SpatialFeature

# Configure logging
logger = logging.getLogger(__name__)

def get_vector_tile(z: int, x: int, y: int, source: Optional[str] = None, layers: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Get a vector tile for the specified tile coordinates
    
    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        source: Optional source system filter
        layers: Optional list of layers to include
        
    Returns:
        Vector tile data in GeoJSON format
    """
    try:
        # Convert tile coordinates to bounding box
        bbox = tile_to_bbox(z, x, y)
        
        # Build SQL query for PostGIS
        query = f"""
        SELECT 
            id, 
            feature_id, 
            feature_type, 
            properties, 
            ST_AsGeoJSON(ST_Simplify(
                ST_Transform(
                    ST_Intersection(
                        geometry, 
                        ST_Transform(
                            ST_MakeEnvelope({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}, 4326),
                            4326
                        )
                    ),
                    3857
                ),
                {simplification_factor_for_zoom(z)}
            )) as geometry,
            source_system,
            is_synced
        FROM 
            spatial_features
        WHERE 
            ST_Intersects(
                geometry, 
                ST_Transform(
                    ST_MakeEnvelope({bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}, 4326),
                    4326
                )
            )
        """
        
        # Add source filter if specified
        if source:
            query += f" AND source_system = '{source}'"
        
        # Add layers filter if specified
        if layers:
            layers_str = "', '".join(layers)
            query += f" AND feature_type IN ('{layers_str}')"
        
        # Execute query
        result = execute_spatial_query(query)
        
        if result["status"] != "success":
            raise Exception(f"Error executing spatial query: {result.get('message')}")
        
        # Convert to GeoJSON
        features = []
        for row in result["data"]:
            # Skip if geometry is null or invalid
            if not row["geometry"]:
                continue
                
            feature = {
                "type": "Feature",
                "id": row["feature_id"],
                "properties": {
                    **(row["properties"] or {}),
                    "id": row["feature_id"],
                    "feature_type": row["feature_type"],
                    "source_system": row["source_system"],
                    "is_synced": row["is_synced"]
                },
                "geometry": json.loads(row["geometry"])
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "bbox": bbox
        }
    except Exception as e:
        logger.error(f"Error generating vector tile {z}/{x}/{y}: {str(e)}")
        raise

def get_feature_info(feature_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific feature
    
    Args:
        feature_id: ID of the feature
        
    Returns:
        Feature information in GeoJSON format
    """
    try:
        # Build SQL query
        query = f"""
        SELECT 
            id, 
            feature_id, 
            feature_type, 
            properties, 
            ST_AsGeoJSON(geometry) as geometry,
            source_system,
            is_synced,
            created_at,
            updated_at
        FROM 
            spatial_features
        WHERE 
            feature_id = '{feature_id}'
        """
        
        # Execute query
        result = execute_spatial_query(query)
        
        if result["status"] != "success" or not result["data"]:
            return None
        
        # Get first (and should be only) row
        row = result["data"][0]
        
        # Convert to GeoJSON
        feature = {
            "type": "Feature",
            "id": row["feature_id"],
            "properties": {
                **(row["properties"] or {}),
                "id": row["feature_id"],
                "feature_type": row["feature_type"],
                "source_system": row["source_system"],
                "is_synced": row["is_synced"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            },
            "geometry": json.loads(row["geometry"])
        }
        
        return feature
    except Exception as e:
        logger.error(f"Error getting feature info for {feature_id}: {str(e)}")
        raise

def get_map_layers() -> List[Dict[str, Any]]:
    """
    Get available map layers
    
    Returns:
        List of layer definitions
    """
    try:
        # Build SQL query to get distinct feature types
        query = """
        SELECT 
            feature_type, 
            COUNT(*) as count,
            MIN(ST_XMin(ST_Envelope(geometry))) as min_x,
            MIN(ST_YMin(ST_Envelope(geometry))) as min_y,
            MAX(ST_XMax(ST_Envelope(geometry))) as max_x,
            MAX(ST_YMax(ST_Envelope(geometry))) as max_y
        FROM 
            spatial_features
        GROUP BY 
            feature_type
        ORDER BY 
            feature_type
        """
        
        # Execute query
        result = execute_spatial_query(query)
        
        if result["status"] != "success":
            raise Exception(f"Error executing layer query: {result.get('message')}")
        
        # Convert to layer definitions
        layers = []
        for row in result["data"]:
            layers.append({
                "id": row["feature_type"],
                "name": row["feature_type"].replace("_", " ").title(),
                "count": row["count"],
                "bounds": [
                    row["min_x"],
                    row["min_y"],
                    row["max_x"],
                    row["max_y"]
                ]
            })
        
        return layers
    except Exception as e:
        logger.error(f"Error getting map layers: {str(e)}")
        raise

def get_map_sources() -> List[Dict[str, Any]]:
    """
    Get available map sources
    
    Returns:
        List of source definitions
    """
    try:
        # Build SQL query to get distinct source systems
        query = """
        SELECT 
            source_system, 
            COUNT(*) as count,
            MIN(ST_XMin(ST_Envelope(geometry))) as min_x,
            MIN(ST_YMin(ST_Envelope(geometry))) as min_y,
            MAX(ST_XMax(ST_Envelope(geometry))) as max_x,
            MAX(ST_YMax(ST_Envelope(geometry))) as max_y
        FROM 
            spatial_features
        GROUP BY 
            source_system
        ORDER BY 
            source_system
        """
        
        # Execute query
        result = execute_spatial_query(query)
        
        if result["status"] != "success":
            raise Exception(f"Error executing source query: {result.get('message')}")
        
        # Convert to source definitions
        sources = []
        for row in result["data"]:
            sources.append({
                "id": row["source_system"],
                "name": row["source_system"].replace("_", " ").title(),
                "count": row["count"],
                "bounds": [
                    row["min_x"],
                    row["min_y"],
                    row["max_x"],
                    row["max_y"]
                ]
            })
        
        return sources
    except Exception as e:
        logger.error(f"Error getting map sources: {str(e)}")
        raise

def tile_to_bbox(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """
    Convert tile coordinates to a bounding box
    
    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        
    Returns:
        Bounding box as (minx, miny, maxx, maxy)
    """
    # Use mercantile library to convert tile to bounding box
    bounds = mercantile.bounds(x, y, z)
    return (bounds.west, bounds.south, bounds.east, bounds.north)

def simplification_factor_for_zoom(z: int) -> float:
    """
    Calculate a simplification factor based on zoom level
    
    Args:
        z: Zoom level
        
    Returns:
        Simplification tolerance
    """
    # Increase simplification as zoom level decreases
    # These values can be tuned based on your data
    if z >= 15:
        return 0.1  # Minimal simplification at high zoom
    elif z >= 12:
        return 1.0
    elif z >= 9:
        return 5.0
    elif z >= 6:
        return 10.0
    else:
        return 20.0  # Maximum simplification at low zoom
