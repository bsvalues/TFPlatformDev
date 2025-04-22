import json
import logging
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from app.core.exceptions import AgentExecutionError
from app.db.postgres import get_db

logger = logging.getLogger(__name__)

class PostGISTools:
    """
    Tools for working with PostGIS spatial operations
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize PostGIS tools with database session
        """
        self.db = db
        logger.info("PostGIS tools initialized")
    
    async def ensure_wkt(self, geometry: str) -> str:
        """
        Ensure geometry is in WKT format
        
        Args:
            geometry: Geometry string in WKT or GeoJSON format
            
        Returns:
            WKT geometry string
        """
        try:
            # Check if already WKT
            if geometry.strip().upper().startswith(('POINT', 'LINESTRING', 'POLYGON', 'MULTIPOINT', 'MULTILINESTRING', 'MULTIPOLYGON', 'GEOMETRYCOLLECTION')):
                return geometry
            
            # Try to parse as GeoJSON
            try:
                geojson = None
                if isinstance(geometry, dict):
                    geojson = geometry
                else:
                    geojson = json.loads(geometry)
                
                # Convert GeoJSON to WKT using PostGIS
                if not self.db:
                    # Get a new DB session if none provided
                    db_session = next(get_db())
                else:
                    db_session = self.db
                
                # Use ST_AsText to convert GeoJSON to WKT
                result = db_session.execute(
                    f"SELECT ST_AsText(ST_GeomFromGeoJSON('{json.dumps(geojson)}')) as wkt"
                ).fetchone()
                
                if result:
                    return result.wkt
                else:
                    raise ValueError("Failed to convert GeoJSON to WKT")
            except json.JSONDecodeError:
                raise ValueError("Invalid GeoJSON or WKT geometry string")
        except Exception as e:
            logger.error(f"Error ensuring WKT format: {str(e)}")
            raise AgentExecutionError(f"Failed to ensure WKT format: {str(e)}")
    
    async def create_buffer(self, geometry: str, distance: float) -> Dict[str, Any]:
        """
        Create a buffer around a geometry
        
        Args:
            geometry: WKT geometry string
            distance: Buffer distance in meters
            
        Returns:
            Buffer result as GeoJSON
        """
        try:
            # Get a DB session if not provided
            if not self.db:
                db_session = next(get_db())
            else:
                db_session = self.db
            
            # Create buffer using PostGIS
            result = db_session.execute(
                f"""
                SELECT ST_AsGeoJSON(
                    ST_Buffer(
                        ST_GeomFromText(:geometry, 4326)::geography, 
                        :distance
                    )::geometry
                ) as geojson
                """,
                {"geometry": geometry, "distance": distance}
            ).fetchone()
            
            if result:
                return json.loads(result.geojson)
            else:
                raise ValueError("Failed to create buffer")
        except Exception as e:
            logger.error(f"Error creating buffer: {str(e)}")
            raise AgentExecutionError(f"Failed to create buffer: {str(e)}")
    
    async def find_intersections(self, geometry: str, target_layer: str) -> Dict[str, Any]:
        """
        Find features that intersect with a geometry
        
        Args:
            geometry: WKT geometry string
            target_layer: Name of the target layer to intersect with
            
        Returns:
            Dictionary with intersection results
        """
        try:
            # Get a DB session if not provided
            if not self.db:
                db_session = next(get_db())
            else:
                db_session = self.db
            
            # Find intersections using PostGIS
            # Note: We use a safeguard to prevent SQL injection by validating target_layer
            valid_layers = ["spatialfeature", "project"]
            if target_layer.lower() not in valid_layers:
                raise ValueError(f"Invalid target layer. Allowed values: {', '.join(valid_layers)}")
            
            result = db_session.execute(
                f"""
                SELECT 
                    id, 
                    name, 
                    feature_type,
                    ST_AsGeoJSON(geometry) as geojson,
                    properties
                FROM 
                    {target_layer}
                WHERE 
                    ST_Intersects(
                        geometry, 
                        ST_GeomFromText(:geometry, 4326)
                    )
                """,
                {"geometry": geometry}
            ).fetchall()
            
            features = []
            for row in result:
                properties = row.properties or {}
                properties.update({
                    "id": str(row.id),
                    "name": row.name,
                    "feature_type": row.feature_type
                })
                
                features.append({
                    "type": "Feature",
                    "geometry": json.loads(row.geojson),
                    "properties": properties
                })
            
            return {
                "type": "FeatureCollection",
                "features": features,
                "count": len(features)
            }
        except Exception as e:
            logger.error(f"Error finding intersections: {str(e)}")
            raise AgentExecutionError(f"Failed to find intersections: {str(e)}")
    
    async def calculate_area(self, geometry: str) -> float:
        """
        Calculate area of a polygon
        
        Args:
            geometry: WKT geometry string
            
        Returns:
            Area in square meters
        """
        try:
            # Get a DB session if not provided
            if not self.db:
                db_session = next(get_db())
            else:
                db_session = self.db
            
            # Calculate area using PostGIS
            result = db_session.execute(
                f"""
                SELECT 
                    ST_Area(
                        ST_GeomFromText(:geometry, 4326)::geography
                    ) as area
                """,
                {"geometry": geometry}
            ).fetchone()
            
            if result:
                return result.area
            else:
                raise ValueError("Failed to calculate area")
        except Exception as e:
            logger.error(f"Error calculating area: {str(e)}")
            raise AgentExecutionError(f"Failed to calculate area: {str(e)}")
