import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import uvicorn

from services.common.auth import get_current_user
from services.terra_map.tiles import (
    get_vector_tile, 
    get_feature_info,
    get_map_layers,
    get_map_sources
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="TerraMap Service",
    description="Map tile and feature service for TerraFusion platform",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "terra_map"}

@app.get("/tiles/{z}/{x}/{y}", response_model=Dict[str, Any])
async def tile_endpoint(
    z: int, 
    x: int, 
    y: int,
    source: Optional[str] = None,
    layers: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get vector tile for the given tile coordinates
    
    Args:
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        source: Optional source name
        layers: Optional comma-separated list of layers
    """
    try:
        # Parse layers if provided
        layer_list = layers.split(",") if layers else None
        
        # Get tile data
        tile_data = get_vector_tile(z, x, y, source, layer_list)
        
        return {
            "status": "success",
            "tile": tile_data
        }
    except Exception as e:
        logger.error(f"Error getting tile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting tile: {str(e)}")

@app.get("/layers", response_model=Dict[str, Any])
async def layers_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get available map layers
    """
    try:
        layers = get_map_layers()
        
        return {
            "status": "success",
            "layers": layers
        }
    except Exception as e:
        logger.error(f"Error getting layers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting layers: {str(e)}")

@app.get("/sources", response_model=Dict[str, Any])
async def sources_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get available map sources
    """
    try:
        sources = get_map_sources()
        
        return {
            "status": "success",
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Error getting sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")

@app.get("/features/{feature_id}", response_model=Dict[str, Any])
async def feature_endpoint(
    feature_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get detailed information about a specific feature
    
    Args:
        feature_id: ID of the feature
    """
    try:
        feature_info = get_feature_info(feature_id)
        
        if not feature_info:
            raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")
        
        return {
            "status": "success",
            "feature": feature_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feature info: {str(e)}")

@app.get("/query", response_model=Dict[str, Any])
async def query_features(
    bbox: str = Query(..., description="Bounding box in format minx,miny,maxx,maxy"),
    layer: Optional[str] = None,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Query features within a bounding box
    
    Args:
        bbox: Bounding box coordinates (minx,miny,maxx,maxy)
        layer: Optional layer name to filter by
        limit: Maximum number of features to return
    """
    try:
        # Parse bounding box
        try:
            minx, miny, maxx, maxy = map(float, bbox.split(","))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bounding box format. Use minx,miny,maxx,maxy")
        
        # Build query
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
            ST_Intersects(geometry, ST_MakeEnvelope({minx}, {miny}, {maxx}, {maxy}, 4326))
        """
        
        if layer:
            query += f" AND feature_type = '{layer}'"
        
        query += f" LIMIT {limit}"
        
        # Execute query
        result = await execute_query(query)
        
        # Convert to GeoJSON
        features = []
        for row in result:
            feature = {
                "type": "Feature",
                "id": row["feature_id"],
                "properties": {
                    **row["properties"],
                    "id": row["feature_id"],
                    "feature_type": row["feature_type"],
                    "source_system": row["source_system"],
                    "is_synced": row["is_synced"]
                },
                "geometry": json.loads(row["geometry"])
            }
            features.append(feature)
        
        return {
            "status": "success",
            "features": features,
            "count": len(features)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying features: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error querying features: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
