"""
FastAPI dependencies for the API service.
"""

import json
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.postgres import get_db
from shared.db.redis import RateLimiter
from shared.models import Organization, User, Website
from shared.utils.jwt import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user."""
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check cache first
    from shared.db.redis import RedisCache
    
    # Use a separate cache prefix for users
    user_cache = RedisCache(prefix="user")
    cached_user_data = await user_cache.get(f"{user_id}")
    
    if cached_user_data:
        try:
            # Reconstruct user object from cached dict
            if isinstance(cached_user_data, str):
                user_data_dict = json.loads(cached_user_data)
            else:
                user_data_dict = cached_user_data

            user = User(**user_data_dict)
            # Ensure it is attached to current session if needed, or use as detached object.
            # Since we are using it for read-only in dependencies, detached is usually fine.
            # However, if we need to update it, we might need to merge it back to session.
            # But get_current_user is mostly for authentication and authorization.
            
            # If we need lazy loading relationships, this might be tricky with detached object.
            # But the User model seems simple.
            pass
        except Exception:
            # Fallback to DB if cache parsing fails
            cached_user_data = None

    if not cached_user_data:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        
        if user and user.is_active:
            # Cache the user data
            # Convert to dict and exclude internal SQLAlchemy state
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "organization_id": str(user.organization_id),
                "role": user.role,
                "is_active": user.is_active,
                "password_hash": user.password_hash # Required for password verification if reused
                # Add other necessary fields
            }
            # Cache for 5 minutes
            await user_cache.set(f"{user_id}", json.dumps(user_dict), ttl=300)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_organization(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Organization:
    """Get the current user's organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = result.scalar_one_or_none()

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


async def get_website(
    website_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Website:
    """Get a website by ID, ensuring it belongs to the user's organization."""
    result = await db.execute(
        select(Website).where(
            Website.id == website_id,
            Website.organization_id == current_user.organization_id,
        )
    )
    website = result.scalar_one_or_none()

    if website is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found",
        )

    return website


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentOrg = Annotated[Organization, Depends(get_current_organization)]
CurrentWebsite = Annotated[Website, Depends(get_website)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_rate_limiter(prefix: str = "api") -> RateLimiter:
    """Get a rate limiter instance."""
    return RateLimiter(prefix=f"ratelimit:{prefix}")
