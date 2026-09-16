from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type, usually 'bearer'")
    role: str = Field(..., description="User role (admin/user)")

class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject (user id)")
    exp: int = Field(..., description="Expiration timestamp (unix epoch)")
    role: str = Field(..., description="User role (admin/user)")

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email for login")
    password: str = Field(..., min_length=6, description="Plain password")
