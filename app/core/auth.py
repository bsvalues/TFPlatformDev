import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import ldap
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, validator

from app.core.config import settings
from app.db.models.user import User
from app.db.postgres import get_db
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str

    @validator("password")
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserInDB(UserBase):
    id: int

    class Config:
        orm_mode = True


def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token for the user
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "iat": datetime.utcnow()}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def authenticate_with_active_directory(username: str, password: str) -> bool:
    """
    Authenticate user with Active Directory LDAP
    """
    if not settings.AD_SERVER or not settings.AD_BASE_DN:
        # AD not configured, skip this authentication method
        return False
    
    try:
        # Initialize LDAP connection
        ldap_client = ldap.initialize(f"ldap://{settings.AD_SERVER}")
        ldap_client.protocol_version = 3
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)
        
        # Try to bind with the user's credentials
        user_dn = f"{username}@{settings.AD_DOMAIN}" if settings.AD_DOMAIN else username
        ldap_client.simple_bind_s(user_dn, password)
        
        # Search for the user in AD
        base_dn = settings.AD_BASE_DN
        search_filter = f"(sAMAccountName={username})"
        
        result = ldap_client.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter)
        
        # If user is found, authentication successful
        if result:
            return True
        
        return False
    except ldap.INVALID_CREDENTIALS:
        return False
    except Exception as e:
        print(f"LDAP Authentication error: {e}")
        return False


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate user with local database or Active Directory
    """
    # Try AD authentication first if configured
    if settings.AD_SERVER and authenticate_with_active_directory(username, password):
        # If AD auth successful, check if user exists in local DB or create if not
        user = db.query(User).filter(User.username == username).first()
        if not user:
            # Create user in local DB for the first time
            user = User(
                username=username,
                email=f"{username}@{settings.AD_DOMAIN}" if settings.AD_DOMAIN else None,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    # Fall back to local DB authentication
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.verify_password(password):
        return None
    return user


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Decode JWT token and get current user
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        token_data = TokenPayload(**payload)
        
        if token_data.exp and datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(User).filter(User.username == token_data.sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    return user


async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Check if current user is a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
