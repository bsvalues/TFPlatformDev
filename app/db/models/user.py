from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.security import get_password_hash, verify_password
from app.db.models.base import BaseModel, TimestampMixin


class User(BaseModel, TimestampMixin):
    """User model for authentication and authorization"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)  # Nullable for AD-authenticated users
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    def set_password(self, password: str) -> None:
        """Set user password (hashed)"""
        self.password_hash = get_password_hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify user password"""
        if not self.password_hash:
            return False
        return verify_password(password, self.password_hash)
