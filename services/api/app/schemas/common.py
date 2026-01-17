"""
Common schemas used across the API.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    page: int
    limit: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def from_params(cls, params: PaginationParams, total: int) -> "PaginationMeta":
        pages = (total + params.limit - 1) // params.limit if params.limit > 0 else 0
        return cls(
            page=params.page,
            limit=params.limit,
            total=total,
            pages=pages,
            has_next=params.page < pages,
            has_prev=params.page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    data: list[T]
    pagination: PaginationMeta


class ErrorDetail(BaseModel):
    """Error detail for validation errors."""

    field: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict[str, Any] = Field(
        ...,
        examples=[
            {
                "code": "validation_error",
                "message": "Invalid request parameters",
                "details": [{"field": "url", "message": "Must be a valid URL"}],
            }
        ],
    )
    request_id: str | None = None


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
