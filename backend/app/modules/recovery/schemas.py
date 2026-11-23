from pydantic import BaseModel, EmailStr, Field
from typing import List

class RecoveryStartRequest(BaseModel):
    email: EmailStr
    recovery_code: str = Field(..., min_length=8, max_length=32)


class RecoveryStartResponse(BaseModel):
    message: str
    recovery_token: str


class RecoveryCompleteRequest(BaseModel):
    recovery_token: str = Field(..., min_length=16)
    new_password: str = Field(..., min_length=8, max_length=128)


class RecoveryCompleteResponse(BaseModel):
    message: str


class RecoveryRegenerateResponse(BaseModel):
    message: str
    recovery_codes: List[str]
