from pydantic import BaseModel, Field
from typing import List, Optional

class MfaEnrolStartResponse(BaseModel):
    secret: str
    secret_grouped: str
    otpauth_uri: str
    qr_code_data_uri: str
    message: str


class MfaEnrolConfirmRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class MfaEnrolConfirmResponse(BaseModel):
    message: str
    recovery_codes: List[str]


class MfaVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10)


class MfaVerifyResponse(BaseModel):
    status: str
    message: str
