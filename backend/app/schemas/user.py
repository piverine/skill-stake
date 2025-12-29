from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
import uuid

class UserBase(BaseModel):
    email: EmailStr
    
class UserCreate(UserBase):
    clerk_id: str = Field(..., min_length=1, max_length=255, description="Clerk authentication ID")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

class UserResponse(UserBase):
    user_id: uuid.UUID
    clerk_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True