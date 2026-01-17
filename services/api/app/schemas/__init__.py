"""
Pydantic schemas for API request/response validation.
"""

from services.api.app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from services.api.app.schemas.website import (
    ScrapeRequest,
    ScrapeResponse,
    WebsiteCreate,
    WebsiteResponse,
    WebsiteListResponse,
)
from services.api.app.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginationParams,
    PaginationMeta,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RefreshRequest",
    "RefreshResponse",
    "RegisterRequest",
    "RegisterResponse",
    "UserResponse",
    # Website
    "WebsiteCreate",
    "WebsiteResponse",
    "WebsiteListResponse",
    "ScrapeRequest",
    "ScrapeResponse",
    # Common
    "ErrorResponse",
    "MessageResponse",
    "PaginationParams",
    "PaginationMeta",
]
