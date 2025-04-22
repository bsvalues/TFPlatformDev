from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.auth import authenticate_user, create_access_token
from app.core.config import settings
from app.db.postgres import get_db
from app.db.models.user import User
from app.core.auth import Token, UserInDB, get_current_user

router = APIRouter()

@router.post("/auth/login", response_model=Token)
async def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    Login endpoint for obtaining JWT access token
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserInDB)
async def read_users_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get current user information
    """
    return current_user


@router.post("/auth/verify", response_model=bool)
async def verify_token(current_user: User = Depends(get_current_user)) -> bool:
    """
    Verify if the token is valid
    """
    return True
