from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    status: str  # "authenticated" | "mfa_pending"
    message: str
    email: str
    mfa_enabled: bool


class AuthMeResponse(BaseModel):
    status: str  # "authenticated" | "mfa_pending" | "unauthenticated"
    user_id: Optional[str] = None
    email: Optional[str] = None
    mfa_enabled: bool = False


class MessageResponse(BaseModel):
    message: str
