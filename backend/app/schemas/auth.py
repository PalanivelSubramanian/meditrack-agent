from pydantic import BaseModel


class AuthStartRequest(BaseModel):
    employee_id: str


class AuthStartResponse(BaseModel):
    requires_totp: bool
    employee_id: str
    message: str


class VerifyTotpRequest(BaseModel):
    employee_id: str
    totp_code: str


class VerifyTotpResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    employee_id: str
    full_name: str
    role: str
    permissions: list[str]


class CurrentUserResponse(BaseModel):
    user_id: int
    employee_id: str
    full_name: str
    role: str
    permissions: list[str]