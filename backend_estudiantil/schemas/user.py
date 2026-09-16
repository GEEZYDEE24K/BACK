from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="Full name of the user")

class UserCreate(UserBase):
    role: Optional[str] = Field(default="user", description="User role, e.g., 'admin' or 'user'")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: str
    role: str = Field(..., description="User role (admin/user)")
    updated_at: str

    class Config:
        orm_mode = True
