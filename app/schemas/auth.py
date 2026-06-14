from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    telephone: str = Field(..., pattern=r"^\+\d{8,15}$")
    nom: str = Field(..., min_length=2, max_length=100)
    prenom: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    email: str | None = None


class RegisterChauffeurRequest(BaseModel):
    telephone: str = Field(..., pattern=r"^\+\d{8,15}$")
    nom: str = Field(..., min_length=2, max_length=100)
    prenom: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    email: str | None = None


class LoginRequest(BaseModel):
    telephone: str
    password: str


class OTPSendRequest(BaseModel):
    telephone: str


class OTPVerifyRequest(BaseModel):
    telephone: str
    code: str = Field(..., min_length=4, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordForgotRequest(BaseModel):
    telephone: str


class PasswordResetRequest(BaseModel):
    telephone: str
    code: str
    new_password: str = Field(..., min_length=8)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)