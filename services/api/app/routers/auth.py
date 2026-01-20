"""
Authentication endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from shared.config import settings
from shared.models import Organization, User
from shared.utils.hashing import hash_password, verify_password
from shared.utils.jwt import create_access_token, create_refresh_token, decode_token

from services.api.app.dependencies import CurrentUser, DBSession
from services.api.app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(request: RegisterRequest, db: DBSession):
    """Register a new user and organization."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create organization
    base_slug = request.organization_name.lower().replace(" ", "-")[:100]
    org_slug = base_slug
    
    # Check if slug exists
    if await db.scalar(select(Organization).where(Organization.slug == org_slug)):
        # Append random suffix to make it unique
        import secrets
        suffix = secrets.token_hex(4)
        # Ensure we don't exceed length limit (assuming 100 chars)
        org_slug = f"{base_slug[:90]}-{suffix}"

    organization = Organization(
        name=request.organization_name,
        slug=org_slug,
    )
    db.add(organization)
    await db.flush()

    # Create user
    user = User(
        organization_id=organization.id,
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return RegisterResponse(
        user=UserResponse.model_validate(user),
        token=token,
        refresh_token=refresh_token,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(request: LoginRequest, db: DBSession):
    """Authenticate user and return tokens."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Generate tokens
    token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(
        user=UserResponse.model_validate(user),
        token=token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
)
async def refresh_token(request: RefreshRequest, db: DBSession):
    """Refresh access token."""
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token = create_access_token({"sub": str(user.id)})

    return RefreshResponse(
        token=token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(current_user: CurrentUser):
    """Logout current user (invalidate session)."""
    # TODO: Add token to blacklist in Redis
    return None


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information."""
    return UserResponse.model_validate(current_user)
