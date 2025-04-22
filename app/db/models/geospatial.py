from geoalchemy2 import Geometry
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.models.base import BaseModel, TimestampMixin, UUIDMixin


class SpatialFeature(BaseModel, UUIDMixin, TimestampMixin):
    """Base model for spatial features"""
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    feature_type = Column(String, nullable=False)  # point, line, polygon, etc.
    properties = Column(JSONB, nullable=True)
    
    # Spatial geometry column - supports all geometry types
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=False)
    
    # Spatial index is auto-created by PostGIS
    
    def __repr__(self):
        return f"<SpatialFeature {self.name} ({self.feature_type})>"


class Project(BaseModel, UUIDMixin, TimestampMixin):
    """Project model for organizing spatial data"""
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
    
    # Spatial features in this project
    features = relationship("ProjectFeature", back_populates="project")
    
    def __repr__(self):
        return f"<Project {self.name}>"


class ProjectFeature(BaseModel, UUIDMixin, TimestampMixin):
    """Join table between projects and features with additional metadata"""
    project_id = Column(UUID(as_uuid=True), ForeignKey('project.id'), nullable=False)
    feature_id = Column(UUID(as_uuid=True), ForeignKey('spatialfeature.id'), nullable=False)
    order = Column(Integer, nullable=True)
    layer_name = Column(String, nullable=True)
    style = Column(JSONB, nullable=True)  # MapLibre style definition
    
    # Relationships
    project = relationship("Project", back_populates="features")
    feature = relationship("SpatialFeature")
    
    def __repr__(self):
        return f"<ProjectFeature {self.layer_name}>"


class TileSource(BaseModel, UUIDMixin, TimestampMixin):
    """Model for map tile sources"""
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # vector, raster, etc.
    url_template = Column(String, nullable=False)
    min_zoom = Column(Integer, default=0)
    max_zoom = Column(Integer, default=18)
    attribution = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<TileSource {self.name} ({self.source_type})>"
