import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from app.db.postgres import Base


class TimestampMixin:
    """Mixin for adding created/updated timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UUIDMixin:
    """Mixin for adding UUID primary key"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class BaseModel(Base):
    """Base model class with common functionality"""
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate tablename from the class name"""
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
