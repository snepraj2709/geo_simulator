"""
ICP (Ideal Customer Profile) endpoints.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from shared.models import ICP
from shared.queue.celery_app import celery_app

from services.api.app.dependencies import CurrentWebsite, DBSession

router = APIRouter()


class ICPResponse(BaseModel):
    """ICP response schema."""

    id: uuid.UUID
    name: str
    description: str | None
    sequence_number: int
    demographics: dict[str, Any]
    professional_profile: dict[str, Any]
    pain_points: list[str]
    goals: list[str]
    motivations: dict[str, Any]
    objections: list[str] | None
    decision_factors: list[str] | None
    information_sources: list[str] | None
    is_active: bool

    class Config:
        from_attributes = True


class ICPListResponse(BaseModel):
    """ICP list response."""

    data: list[ICPResponse]


class ICPUpdate(BaseModel):
    """ICP update request."""

    name: str | None = None
    pain_points: list[str] | None = None
    goals: list[str] | None = None
    is_active: bool | None = None


class RegenerateResponse(BaseModel):
    """ICP regeneration response."""

    job_id: uuid.UUID
    status: str
    message: str


@router.get(
    "",
    response_model=ICPListResponse,
)
async def list_icps(
    website: CurrentWebsite,
    db: DBSession,
):
    """List ICPs for a website."""
    result = await db.execute(
        select(ICP)
        .where(ICP.website_id == website.id)
        .order_by(ICP.sequence_number)
    )
    icps = result.scalars().all()

    return ICPListResponse(data=[ICPResponse.model_validate(icp) for icp in icps])


@router.get(
    "/{icp_id}",
    response_model=ICPResponse,
)
async def get_icp(
    icp_id: uuid.UUID,
    website: CurrentWebsite,
    db: DBSession,
):
    """Get ICP details."""
    result = await db.execute(
        select(ICP).where(
            ICP.id == icp_id,
            ICP.website_id == website.id,
        )
    )
    icp = result.scalar_one_or_none()

    if icp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICP not found",
        )

    return ICPResponse.model_validate(icp)


@router.put(
    "/{icp_id}",
    response_model=ICPResponse,
)
async def update_icp(
    icp_id: uuid.UUID,
    request: ICPUpdate,
    website: CurrentWebsite,
    db: DBSession,
):
    """Update an ICP."""
    result = await db.execute(
        select(ICP).where(
            ICP.id == icp_id,
            ICP.website_id == website.id,
        )
    )
    icp = result.scalar_one_or_none()

    if icp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICP not found",
        )

    # Update fields
    if request.name is not None:
        icp.name = request.name
    if request.pain_points is not None:
        icp.pain_points = request.pain_points
    if request.goals is not None:
        icp.goals = request.goals
    if request.is_active is not None:
        icp.is_active = request.is_active

    return ICPResponse.model_validate(icp)


@router.post(
    "/regenerate",
    response_model=RegenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def regenerate_icps(
    website: CurrentWebsite,
):
    """Regenerate all ICPs for a website."""
    job_id = uuid.uuid4()

    celery_app.send_task(
        "services.classifier.app.tasks.generate_icps",
        args=[str(website.id)],
        task_id=str(job_id),
        queue="classification",
    )

    return RegenerateResponse(
        job_id=job_id,
        status="queued",
        message="ICP regeneration started. This will also regenerate conversations.",
    )
