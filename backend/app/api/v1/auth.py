from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user, get_optional_user
from app.models.user import User
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter()

class UserResponse(BaseModel):
    user_id: str
    clerk_id: str
    email: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AuthVerifyResponse(BaseModel):
    valid: bool
    user: Optional[UserResponse] = None
    message: str

@router.post("/verify", response_model=AuthVerifyResponse)
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """
    Verify JWT token validity and return user information
    """
    return AuthVerifyResponse(
        valid=True,
        user=UserResponse.model_validate(current_user),
        message="Token is valid"
    )

@router.get("/user", response_model=UserResponse)
async def get_authenticated_user(
    current_user: User = Depends(get_current_user)
):
    """
    Get authenticated user profile
    """
    return UserResponse.model_validate(current_user)

@router.get("/user/optional")
async def get_user_optional(
    user: Optional[User] = Depends(get_optional_user)
):
    """
    Endpoint that works with or without authentication
    """
    if user:
        return {
            "authenticated": True,
            "user": UserResponse.model_validate(user)
        }
    else:
        return {
            "authenticated": False,
            "message": "No authentication provided"
        }