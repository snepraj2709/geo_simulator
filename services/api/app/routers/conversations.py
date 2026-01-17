"""
Conversation endpoints.
"""

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from shared.models import ConversationSequence, Prompt, PromptClassification

from services.api.app.dependencies import CurrentWebsite, DBSession
from services.api.app.schemas.common import PaginationMeta, PaginationParams

router = APIRouter()


class ClassificationResponse(BaseModel):
    """Prompt classification response."""

    intent_type: str
    funnel_stage: str
    buying_signal: Decimal
    trust_need: Decimal
    query_intent: str | None

    class Config:
        from_attributes = True


class PromptResponse(BaseModel):
    """Prompt response."""

    id: uuid.UUID
    prompt_text: str
    prompt_type: str
    sequence_order: int
    classification: ClassificationResponse | None = None

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Conversation list item."""

    id: uuid.UUID
    icp_id: uuid.UUID
    topic: str
    context: str | None
    is_core_conversation: bool
    sequence_number: int
    prompt_count: int = 0

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Conversation list response."""

    data: list[ConversationListItem]
    pagination: PaginationMeta


class ConversationDetailResponse(BaseModel):
    """Conversation detail response."""

    id: uuid.UUID
    icp_id: uuid.UUID
    topic: str
    context: str | None
    expected_outcome: str | None
    is_core_conversation: bool
    prompts: list[PromptResponse]

    class Config:
        from_attributes = True


@router.get(
    "",
    response_model=ConversationListResponse,
)
async def list_conversations(
    website: CurrentWebsite,
    db: DBSession,
    icp_id: uuid.UUID | None = Query(default=None),
    is_core: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List conversation sequences."""
    params = PaginationParams(page=page, limit=limit)

    # Build query
    query = select(ConversationSequence).where(
        ConversationSequence.website_id == website.id
    )

    if icp_id:
        query = query.where(ConversationSequence.icp_id == icp_id)

    if is_core is not None:
        query = query.where(ConversationSequence.is_core_conversation == is_core)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.offset(params.offset).limit(params.limit)
    query = query.order_by(
        ConversationSequence.icp_id,
        ConversationSequence.sequence_number,
    )
    result = await db.execute(query)
    conversations = result.scalars().all()

    # Get prompt counts
    items = []
    for conv in conversations:
        prompt_count = await db.scalar(
            select(func.count()).select_from(Prompt).where(Prompt.conversation_id == conv.id)
        )
        item = ConversationListItem(
            id=conv.id,
            icp_id=conv.icp_id,
            topic=conv.topic,
            context=conv.context,
            is_core_conversation=conv.is_core_conversation,
            sequence_number=conv.sequence_number,
            prompt_count=prompt_count or 0,
        )
        items.append(item)

    return ConversationListResponse(
        data=items,
        pagination=PaginationMeta.from_params(params, total),
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: uuid.UUID,
    website: CurrentWebsite,
    db: DBSession,
):
    """Get conversation with all prompts."""
    result = await db.execute(
        select(ConversationSequence)
        .where(
            ConversationSequence.id == conversation_id,
            ConversationSequence.website_id == website.id,
        )
        .options(
            selectinload(ConversationSequence.prompts).selectinload(Prompt.classification)
        )
    )
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Build prompts with classifications
    prompts = []
    for prompt in sorted(conversation.prompts, key=lambda p: p.sequence_order):
        classification = None
        if prompt.classification:
            classification = ClassificationResponse.model_validate(prompt.classification)

        prompts.append(
            PromptResponse(
                id=prompt.id,
                prompt_text=prompt.prompt_text,
                prompt_type=prompt.prompt_type,
                sequence_order=prompt.sequence_order,
                classification=classification,
            )
        )

    return ConversationDetailResponse(
        id=conversation.id,
        icp_id=conversation.icp_id,
        topic=conversation.topic,
        context=conversation.context,
        expected_outcome=conversation.expected_outcome,
        is_core_conversation=conversation.is_core_conversation,
        prompts=prompts,
    )
