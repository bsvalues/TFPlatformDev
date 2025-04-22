from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.models.base import BaseModel, TimestampMixin, UUIDMixin
from app.db.models.user import User


class AuditLog(BaseModel, UUIDMixin, TimestampMixin):
    """Audit log for tracking changes to data"""
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=True)
    action = Column(String, nullable=False)  # create, update, delete, etc.
    resource_type = Column(String, nullable=False)  # table/model name
    resource_id = Column(String, nullable=False)  # ID of the affected record
    before_state = Column(JSONB, nullable=True)  # JSON representation before change
    after_state = Column(JSONB, nullable=True)  # JSON representation after change
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource_type}:{self.resource_id}>"


class DataCorrection(BaseModel, UUIDMixin, TimestampMixin):
    """Model for tracking and applying data corrections"""
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=True)
    feature_id = Column(UUID(as_uuid=True), ForeignKey('spatialfeature.id'), nullable=False)
    correction_type = Column(String, nullable=False)  # geometry, attribute, etc.
    reason = Column(Text, nullable=True)
    original_value = Column(JSONB, nullable=True)
    corrected_value = Column(JSONB, nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    
    # Relationships
    user = relationship("User")
    feature = relationship("SpatialFeature")
    
    def __repr__(self):
        return f"<DataCorrection {self.correction_type} for {self.feature_id}>"
