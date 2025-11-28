"""User Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Base schema with common User fields."""
    
    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new User."""
    
    password: str


class UserUpdate(BaseModel):
    """Schema for updating an existing User.
    
    All fields are optional to allow partial updates.
    """
    
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserRead(UserBase):
    """Schema for reading User data.
    
    Excludes sensitive fields like hashed_password.
    """
    
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
