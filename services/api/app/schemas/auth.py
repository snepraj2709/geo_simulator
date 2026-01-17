"""
Authentication schemas.
"""

import uuid

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    organization_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User information response."""

    id: uuid.UUID
    email: str
    name: str | None
    organization_id: uuid.UUID
    role: str

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    """Registration response."""

    user: UserResponse
    token: str
    refresh_token: str


class LoginResponse(BaseModel):
    """Login response."""

    user: UserResponse
    token: str
    refresh_token: str
    expires_in: int


class RefreshResponse(BaseModel):
    """Token refresh response."""

    token: str
    expires_in: int
