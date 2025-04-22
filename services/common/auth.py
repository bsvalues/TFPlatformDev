import os
import logging
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import ldap

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer()

# LDAP configuration for Active Directory integration
LDAP_SERVER = os.getenv("LDAP_SERVER", "ldap://activedirectory.county.local")
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "DC=county,DC=local")
LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", "")
LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", "")

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-for-development-only")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

class AuthService:
    """
    Authentication service for TerraFusion platform that integrates with County Active Directory
    """
    @staticmethod
    def authenticate_with_ldap(username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user against County Active Directory
        
        Args:
            username: Username or email
            password: User password
            
        Returns:
            Dictionary with authentication result
        """
        try:
            # Connect to LDAP server
            ldap_conn = ldap.initialize(LDAP_SERVER)
            ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
            
            # User DN format for Active Directory
            user_dn = f"CN={username},{LDAP_BASE_DN}"
            
            # Attempt to bind with user credentials
            ldap_conn.simple_bind_s(user_dn, password)
            
            # If the bind is successful, search for user details
            search_filter = f"(sAMAccountName={username})"
            search_attrs = ["displayName", "mail", "memberOf"]
            
            # Execute search
            result = ldap_conn.search_s(
                LDAP_BASE_DN,
                ldap.SCOPE_SUBTREE,
                search_filter,
                search_attrs
            )
            
            # Process user data
            user_data = {}
            if result:
                _, attributes = result[0]
                user_data = {
                    "username": username,
                    "display_name": attributes.get("displayName", [b""])[0].decode(),
                    "email": attributes.get("mail", [b""])[0].decode(),
                    "groups": [g.decode().split(",")[0].split("=")[1] for g in attributes.get("memberOf", [])]
                }
            
            # Create JWT token
            access_token = AuthService.create_access_token(
                data={"sub": username, "groups": user_data.get("groups", [])}
            )
            
            return {
                "status": "success",
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_data
            }
            
        except ldap.INVALID_CREDENTIALS:
            logger.warning(f"Invalid credentials for user: {username}")
            return {"status": "error", "message": "Invalid username or password"}
        except ldap.SERVER_DOWN:
            logger.error("LDAP server is down or unreachable")
            return {"status": "error", "message": "Authentication service unavailable"}
        except Exception as e:
            logger.error(f"LDAP authentication error: {str(e)}")
            return {"status": "error", "message": "Authentication error"}
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token
        
        Args:
            data: Payload data
            expires_delta: Token expiration time
            
        Returns:
            JWT token as string
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta
            if expires_delta
            else timedelta(minutes=JWT_EXPIRATION_MINUTES)
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

# Dependency for routes that require authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token
    """
    try:
        token = credentials.credentials
        payload = AuthService.decode_token(token)
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Check if user has specific role
def has_role(required_roles: List[str]):
    """
    Dependency for routes that require specific roles
    """
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_groups = current_user.get("groups", [])
        for role in required_roles:
            if role in user_groups:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return role_checker
