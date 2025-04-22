from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.models.geospatial import SpatialFeature, TileSource
from app.db.models.user import User
from app.db.postgres import get_db

router = APIRouter()

@router.get("/sources", status_code=status.HTTP_200_OK)
async def get_tile_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get available tile sources for map
    """
    try:
        sources = db.query(TileSource).all()
        return [source.to_dict() for source in sources]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tile sources: {str(e)}"
        )


@router.get("/features", status_code=status.HTTP_200_OK)
async def get_spatial_features(
    bbox: Optional[str] = Query(None, description="Bounding box (minLon,minLat,maxLon,maxLat)"),
    feature_type: Optional[str] = Query(None, description="Type of feature to filter by"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of features to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get spatial features for map display
    """
    try:
        query = db.query(SpatialFeature)
        
        # Apply filters
        if feature_type:
            query = query.filter(SpatialFeature.feature_type == feature_type)
            
        # Apply spatial filter if bbox provided
        if bbox:
            try:
                min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
                bbox_wkt = f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
                query = query.filter(SpatialFeature.geometry.ST_Intersects(f"ST_GeomFromText('{bbox_wkt}', 4326)"))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid bbox format. Expected 'minLon,minLat,maxLon,maxLat'"
                )
                
        # Apply limit
        features = query.limit(limit).all()
        
        # Convert to GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        for feature in features:
            properties = feature.properties or {}
            properties.update({
                "id": str(feature.id),
                "name": feature.name,
                "feature_type": feature.feature_type,
                "description": feature.description
            })
            
            # Get GeoJSON geometry from PostGIS
            geometry_result = db.execute(
                f"SELECT ST_AsGeoJSON(geometry) as geom FROM spatialfeature WHERE id = '{feature.id}'"
            ).fetchone()
            
            if geometry_result:
                geojson["features"].append({
                    "type": "Feature",
                    "geometry": eval(geometry_result.geom),
                    "properties": properties
                })
                
        return geojson
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving spatial features: {str(e)}"
        )


@router.get("/feature/{feature_id}", status_code=status.HTTP_200_OK)
async def get_spatial_feature(
    feature_id: str = Path(..., description="ID of the spatial feature"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get a specific spatial feature by ID
    """
    try:
        feature = db.query(SpatialFeature).filter(SpatialFeature.id == feature_id).first()
        
        if not feature:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature with ID {feature_id} not found"
            )
            
        # Get GeoJSON geometry from PostGIS
        geometry_result = db.execute(
            f"SELECT ST_AsGeoJSON(geometry) as geom FROM spatialfeature WHERE id = '{feature.id}'"
        ).fetchone()
        
        if not geometry_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving feature geometry"
            )
            
        properties = feature.properties or {}
        properties.update({
            "id": str(feature.id),
            "name": feature.name,
            "feature_type": feature.feature_type,
            "description": feature.description,
            "created_at": feature.created_at.isoformat(),
            "updated_at": feature.updated_at.isoformat()
        })
        
        return {
            "type": "Feature",
            "geometry": eval(geometry_result.geom),
            "properties": properties
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving spatial feature: {str(e)}"
        )


@router.get("/styles/{style_id}", status_code=status.HTTP_200_OK)
async def get_map_style(
    style_id: str = Path(..., description="ID of the map style"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get MapLibre style definition
    """
    try:
        # For demonstration, return a sample style
        # In production, this would be retrieved from the database
        if style_id == "default":
            return {
                "version": 8,
                "name": "TerraFusion Default",
                "sources": {
                    "osm": {
                        "type": "raster",
                        "tiles": ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                        "tileSize": 256,
                        "attribution": "© OpenStreetMap contributors"
                    }
                },
                "layers": [
                    {
                        "id": "osm-tiles",
                        "type": "raster",
                        "source": "osm",
                        "minzoom": 0,
                        "maxzoom": 19
                    }
                ]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Style with ID {style_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving map style: {str(e)}"
        )
