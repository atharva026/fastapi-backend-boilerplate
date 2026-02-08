import uuid
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from src.app.models.user import UserType

class UserBase(BaseModel):
    email: EmailStr
    name: str
    user_type: UserType = UserType.USER

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: str

class UserInDB(UserBase):
    id: uuid.UUID
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
class UserResponse(UserInDB):
    pass
