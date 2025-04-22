import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

# Import Base from database module
from services.common.database import Base

class User(Base):
    """User model for application users"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    display_name = Column(String(128))
    ad_groups = Column(JSONB)  # Store Active Directory groups as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    tasks = relationship("Task", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"

class SpatialFeature(Base):
    """Spatial feature model for geospatial data"""
    __tablename__ = "spatial_features"

    id = Column(Integer, primary_key=True, index=True)
    feature_id = Column(String(64), unique=True, nullable=False)
    feature_type = Column(String(32), nullable=False)
    properties = Column(JSONB)  # Store feature properties as JSON
    geometry = Column(Geometry(geometry_type='GEOMETRY', srid=4326), nullable=False)
    source_system = Column(String(64))  # Which system this feature came from
    is_synced = Column(Boolean, default=False)  # Whether it's synced with JCHARRISPACS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="feature")

    def __repr__(self):
        return f"<SpatialFeature {self.feature_id}>"

    def to_geojson(self) -> Dict[str, Any]:
        """Convert to GeoJSON format"""
        properties = self.properties.copy() if self.properties else {}
        properties.update({
            "id": self.feature_id,
            "type": self.feature_type,
            "source_system": self.source_system,
            "is_synced": self.is_synced,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        })
        
        return {
            "type": "Feature",
            "id": self.id,
            "properties": properties,
            "geometry": json.loads(self.geometry)
        }

class Task(Base):
    """Task model for tracking ETL and processing jobs"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(32), nullable=False)  # ETL, AI, Audit, etc.
    status = Column(String(16), default="pending")  # pending, running, completed, failed
    parameters = Column(JSONB)  # Task parameters
    result = Column(JSONB)  # Task result
    error_message = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))  # Who initiated the task
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.id} ({self.task_type})>"

class AuditLog(Base):
    """Audit log model for tracking changes"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(32), nullable=False)  # create, update, delete, etc.
    entity_type = Column(String(32), nullable=False)  # What type of entity was changed
    entity_id = Column(Integer, nullable=False)  # ID of the entity that was changed
    before_state = Column(JSONB)  # State before change
    after_state = Column(JSONB)  # State after change
    user_id = Column(Integer, ForeignKey("users.id"))  # Who made the change
    feature_id = Column(Integer, ForeignKey("spatial_features.id"), nullable=True)  # If change affects spatial feature
    ip_address = Column(String(64))  # IP address of the requester
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    feature = relationship("SpatialFeature", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.id} ({self.action})>"

class SyncRecord(Base):
    """Sync record model for tracking synchronization with JCHARRISPACS"""
    __tablename__ = "sync_records"

    id = Column(Integer, primary_key=True, index=True)
    source_system = Column(String(64), nullable=False)  # JCHARRISPACS, TerraFusion, etc.
    entity_type = Column(String(32), nullable=False)  # What type of entity was synced
    entity_id = Column(Integer, nullable=False)  # ID of the entity in the source system
    target_id = Column(Integer, nullable=True)  # ID in the target system
    sync_direction = Column(String(16), nullable=False)  # inbound, outbound
    sync_status = Column(String(16), default="pending")  # pending, completed, failed
    error_message = Column(Text)
    sync_timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SyncRecord {self.id} ({self.source_system} -> {self.entity_type})>"
