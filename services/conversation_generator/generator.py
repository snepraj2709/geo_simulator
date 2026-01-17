"""
Conversation Generator service.

Generates realistic conversation topics and prompts using LLM analysis of ICPs.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.llm import LLMClient, LLMProvider, get_llm_client, ResponseFormat
from shared.models.conversation import ConversationSequence, Prompt
from shared.models.icp import ICP
from shared.models.website import Website, WebsiteAnalysis

from services.conversation_generator.schemas import (
    ConversationGenerationResponse,
    GeneratedConversation,
    GeneratedPrompt,
    PromptType,
)
from services.conversation_generator.prompts import (
    CONVERSATION_SYSTEM_PROMPT,
    build_conversation_prompt_from_models,
)

logger = logging.getLogger(__name__)


class ConversationGenerationError(Exception):
    """Error during conversation generation."""
    pass


class ConversationGenerator:
    """
    Generates conversation topics and prompts for ICPs using LLM.

    Features:
    - Generates 10 conversations per ICP (5 core + 5 variable)
    - Each conversation has 1 primary + 3-5 follow-up prompts
    - Validates uniqueness and relevance
    - Supports multiple LLM providers
    """

    MAX_RETRIES = 3
    DEFAULT_TEMPERATURE = 0.6  # Slightly higher for creative conversation generation
    CONVERSATIONS_PER_ICP = 10
    CORE_CONVERSATIONS = 5

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        llm_provider: LLMProvider | str = LLMProvider.OPENAI,
    ):
        """
        Initialize Conversation Generator.

        Args:
            llm_client: Pre-configured LLM client (optional).
            llm_provider: LLM provider to use if client not provided.
        """
        if llm_client:
            self._client = llm_client
        else:
            self._client = get_llm_client(llm_provider)

    async def generate_conversations(
        self,
        icp_id: uuid.UUID,
        session: AsyncSession,
        force_regenerate: bool = False,
    ) -> list[ConversationSequence]:
        """
        Generate conversations for an ICP.

        Args:
            icp_id: UUID of the ICP.
            session: Database session.
            force_regenerate: Whether to regenerate if conversations exist.

        Returns:
            List of generated ConversationSequence models.

        Raises:
            ConversationGenerationError: If generation fails.
        """
        # Check for existing conversations
        if not force_regenerate:
            existing = await self._get_existing_conversations(icp_id, session)
            if existing:
                logger.info("Using existing conversations for ICP %s", icp_id)
                return existing

        # Get ICP and website context
        icp = await self._get_icp(icp_id, session)
        if not icp:
            raise ConversationGenerationError(f"ICP not found: {icp_id}")

        website_context = await self._build_website_context(icp.website_id, session)
        if not website_context:
            raise ConversationGenerationError(f"Website not found for ICP: {icp_id}")

        icp_data = self._build_icp_data(icp)

        logger.info("Generating conversations for ICP %s (%s)", icp_id, icp.name)

        # Generate conversations with retries
        generated_conversations = await self._generate_with_retries(
            website_context=website_context,
            icp_data=icp_data,
        )

        # Delete existing conversations if regenerating
        if force_regenerate:
            await self._delete_existing_conversations(icp_id, session)

        # Store in database
        stored_conversations = await self._store_conversations(
            icp_id=icp_id,
            website_id=icp.website_id,
            generated_conversations=generated_conversations,
            session=session,
        )

        logger.info(
            "Successfully generated %d conversations for ICP %s",
            len(stored_conversations),
            icp_id,
        )
        return stored_conversations

    async def generate_batch(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
        force_regenerate: bool = False,
    ) -> dict[uuid.UUID, list[ConversationSequence]]:
        """
        Generate conversations for all ICPs of a website.

        Args:
            website_id: UUID of the website.
            session: Database session.
            force_regenerate: Whether to regenerate existing conversations.

        Returns:
            Dict mapping ICP IDs to their conversation lists.

        Raises:
            ConversationGenerationError: If generation fails.
        """
        # Get all ICPs for the website
        icps = await self._get_website_icps(website_id, session)
        if not icps:
            raise ConversationGenerationError(f"No ICPs found for website: {website_id}")

        results = {}
        errors = []

        for icp in icps:
            try:
                conversations = await self.generate_conversations(
                    icp_id=icp.id,
                    session=session,
                    force_regenerate=force_regenerate,
                )
                results[icp.id] = conversations
                logger.info(
                    "Generated %d conversations for ICP %s (%s)",
                    len(conversations),
                    icp.id,
                    icp.name,
                )
            except Exception as e:
                logger.error("Failed to generate conversations for ICP %s: %s", icp.id, e)
                errors.append((icp.id, str(e)))

        if errors and not results:
            raise ConversationGenerationError(
                f"All conversation generations failed: {errors}"
            )

        if errors:
            logger.warning("Some ICP conversation generations failed: %s", errors)

        return results

    async def _generate_with_retries(
        self,
        website_context: dict,
        icp_data: dict,
    ) -> list[GeneratedConversation]:
        """
        Generate conversations with retry logic.

        Args:
            website_context: Website/company context.
            icp_data: ICP data dictionary.

        Returns:
            List of validated GeneratedConversation objects.

        Raises:
            ConversationGenerationError: If all retries fail.
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Build prompt
                prompt = build_conversation_prompt_from_models(
                    website_context=website_context,
                    icp=icp_data,
                )

                # Call LLM
                response = await self._client.complete_json(
                    prompt=prompt,
                    system_prompt=CONVERSATION_SYSTEM_PROMPT,
                    temperature=self.DEFAULT_TEMPERATURE,
                    max_tokens=10000,
                )

                if not response.success:
                    raise ConversationGenerationError("LLM returned empty response")

                # Parse response
                raw_json = response.get_json()

                # Handle both direct conversations array and wrapped response
                if isinstance(raw_json, dict) and "conversations" in raw_json:
                    conversations_data = raw_json["conversations"]
                elif isinstance(raw_json, list):
                    conversations_data = raw_json
                else:
                    raise ConversationGenerationError(
                        "Invalid response format: expected conversations array"
                    )

                # Parse and validate each conversation
                parsed_conversations = []
                for i, conv_data in enumerate(conversations_data):
                    # Ensure required fields
                    if "sequence_number" not in conv_data:
                        conv_data["sequence_number"] = i + 1
                    if "is_core_conversation" not in conv_data:
                        conv_data["is_core_conversation"] = i < self.CORE_CONVERSATIONS

                    conversation = GeneratedConversation.model_validate(conv_data)
                    parsed_conversations.append(conversation)

                # Validate response structure
                icp_response = ConversationGenerationResponse(
                    icp_id=uuid.uuid4(),  # Placeholder for validation
                    icp_name=icp_data.get("name", "Unknown"),
                    conversations=parsed_conversations,
                )

                # Additional quality checks
                self._validate_quality(icp_response.conversations)

                logger.info(
                    "Conversation generation succeeded on attempt %d (tokens: %d, latency: %dms)",
                    attempt + 1,
                    response.tokens_used,
                    response.latency_ms,
                )

                return icp_response.conversations

            except ValidationError as e:
                last_error = e
                logger.warning(
                    "Conversation validation failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:300],
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "Conversation generation failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:300],
                )

        raise ConversationGenerationError(
            f"Failed to generate valid conversations after {self.MAX_RETRIES} attempts: {last_error}"
        )

    def _validate_quality(self, conversations: list[GeneratedConversation]) -> None:
        """
        Validate conversation quality and diversity.

        Args:
            conversations: List of generated conversations.

        Raises:
            ValueError: If quality checks fail.
        """
        if len(conversations) != self.CONVERSATIONS_PER_ICP:
            raise ValueError(
                f"Expected {self.CONVERSATIONS_PER_ICP} conversations, got {len(conversations)}"
            )

        # Check topic uniqueness (basic similarity check)
        topics = [c.topic.lower().strip() for c in conversations]
        if len(set(topics)) != len(topics):
            raise ValueError("Conversation topics must be unique")

        # Check for minimum topic length diversity
        topic_lengths = [len(t.split()) for t in topics]
        if max(topic_lengths) - min(topic_lengths) < 2:
            logger.warning("Topics have similar lengths, may lack diversity")

        # Validate core conversations
        core_count = sum(1 for c in conversations if c.is_core_conversation)
        if core_count != self.CORE_CONVERSATIONS:
            raise ValueError(
                f"Expected {self.CORE_CONVERSATIONS} core conversations, got {core_count}"
            )

        # Validate prompt structure for each conversation
        for conv in conversations:
            primary_count = sum(
                1 for p in conv.prompts if p.prompt_type == PromptType.PRIMARY
            )
            if primary_count != 1:
                raise ValueError(
                    f"Conversation '{conv.topic}' must have exactly 1 primary prompt"
                )

            follow_up_count = len(conv.prompts) - 1
            if follow_up_count < 3:
                raise ValueError(
                    f"Conversation '{conv.topic}' must have at least 3 follow-up prompts"
                )

    def _build_icp_data(self, icp: ICP) -> dict:
        """Build ICP data dictionary for prompt generation."""
        return {
            "name": icp.name,
            "description": icp.description,
            "job_role": icp.professional_profile.get("job_role", "Professional"),
            "industry": icp.professional_profile.get("industry", "Unknown"),
            "company_size": icp.professional_profile.get("company_size", "Medium"),
            "demographics": icp.demographics or {},
            "pain_points": icp.pain_points or [],
            "goals": icp.goals or [],
            "decision_factors": icp.decision_factors or [],
            "communication_style": icp.professional_profile.get(
                "communication_style", "Professional"
            ),
            "behavior_patterns": {
                "research_behavior": icp.professional_profile.get(
                    "research_behavior", "Online research"
                ),
                "preferred_channels": icp.information_sources or ["Email", "Chat"],
            },
        }

    async def _build_website_context(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
    ) -> dict | None:
        """Build website context for conversation generation."""
        # Get website
        result = await session.execute(
            select(Website).where(Website.id == website_id)
        )
        website = result.scalar_one_or_none()

        if not website:
            return None

        # Get analysis
        analysis_result = await session.execute(
            select(WebsiteAnalysis).where(WebsiteAnalysis.website_id == website_id)
        )
        analysis = analysis_result.scalar_one_or_none()

        context = {
            "company_name": website.name or website.domain,
            "domain": website.domain,
            "industry": analysis.industry if analysis else "Unknown",
            "products": analysis.primary_offerings[:5] if analysis and analysis.primary_offerings else [],
            "services": [],
            "value_propositions": analysis.value_propositions[:3] if analysis and analysis.value_propositions else [],
        }

        # Add detailed products/services if available
        if analysis:
            if analysis.products_detailed:
                context["products"] = [
                    p.get("name", "") for p in analysis.products_detailed[:5]
                    if isinstance(p, dict)
                ]
            if analysis.services_detailed:
                context["services"] = [
                    s.get("name", "") for s in analysis.services_detailed[:5]
                    if isinstance(s, dict)
                ]

        return context

    async def _get_icp(
        self,
        icp_id: uuid.UUID,
        session: AsyncSession,
    ) -> ICP | None:
        """Get an ICP by ID."""
        result = await session.execute(
            select(ICP).where(ICP.id == icp_id)
        )
        return result.scalar_one_or_none()

    async def _get_website_icps(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[ICP]:
        """Get all active ICPs for a website."""
        result = await session.execute(
            select(ICP)
            .where(ICP.website_id == website_id)
            .where(ICP.is_active == True)
            .order_by(ICP.sequence_number)
        )
        return list(result.scalars().all())

    async def _get_existing_conversations(
        self,
        icp_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[ConversationSequence]:
        """Get existing conversations for an ICP."""
        result = await session.execute(
            select(ConversationSequence)
            .where(ConversationSequence.icp_id == icp_id)
            .options(selectinload(ConversationSequence.prompts))
            .order_by(ConversationSequence.sequence_number)
        )
        return list(result.scalars().all())

    async def _delete_existing_conversations(
        self,
        icp_id: uuid.UUID,
        session: AsyncSession,
    ) -> int:
        """Delete existing conversations for an ICP."""
        # Delete prompts first (foreign key constraint)
        conv_ids_result = await session.execute(
            select(ConversationSequence.id).where(
                ConversationSequence.icp_id == icp_id
            )
        )
        conv_ids = [row[0] for row in conv_ids_result.fetchall()]

        if conv_ids:
            await session.execute(
                delete(Prompt).where(Prompt.conversation_id.in_(conv_ids))
            )

        # Delete conversations
        result = await session.execute(
            delete(ConversationSequence).where(
                ConversationSequence.icp_id == icp_id
            )
        )
        await session.commit()
        return result.rowcount

    async def _store_conversations(
        self,
        icp_id: uuid.UUID,
        website_id: uuid.UUID,
        generated_conversations: list[GeneratedConversation],
        session: AsyncSession,
    ) -> list[ConversationSequence]:
        """
        Store generated conversations in the database.

        Args:
            icp_id: ICP UUID.
            website_id: Website UUID.
            generated_conversations: List of generated conversations.
            session: Database session.

        Returns:
            List of stored ConversationSequence models.
        """
        stored = []

        for gen_conv in generated_conversations:
            # Create conversation sequence
            conversation = ConversationSequence(
                id=uuid.uuid4(),
                website_id=website_id,
                icp_id=icp_id,
                topic=gen_conv.topic,
                context=gen_conv.context,
                expected_outcome=gen_conv.expected_outcome,
                is_core_conversation=gen_conv.is_core_conversation,
                sequence_number=gen_conv.sequence_number,
            )
            session.add(conversation)

            # Create prompts
            for gen_prompt in gen_conv.prompts:
                prompt = Prompt(
                    id=uuid.uuid4(),
                    conversation_id=conversation.id,
                    prompt_text=gen_prompt.prompt_text,
                    prompt_type=gen_prompt.prompt_type,
                    sequence_order=gen_prompt.sequence_order,
                )
                session.add(prompt)

            stored.append(conversation)

        await session.commit()

        # Refresh to get generated timestamps and load prompts
        for conv in stored:
            await session.refresh(conv)

        return stored


async def get_conversations_for_icp(
    icp_id: uuid.UUID,
    session: AsyncSession,
    include_prompts: bool = True,
) -> list[ConversationSequence]:
    """
    Get conversations for an ICP.

    Args:
        icp_id: ICP UUID.
        session: Database session.
        include_prompts: Whether to eagerly load prompts.

    Returns:
        List of ConversationSequence models.
    """
    query = (
        select(ConversationSequence)
        .where(ConversationSequence.icp_id == icp_id)
        .order_by(ConversationSequence.sequence_number)
    )

    if include_prompts:
        query = query.options(selectinload(ConversationSequence.prompts))

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_conversation_by_id(
    conversation_id: uuid.UUID,
    session: AsyncSession,
) -> ConversationSequence | None:
    """
    Get a single conversation by ID with its prompts.

    Args:
        conversation_id: Conversation UUID.
        session: Database session.

    Returns:
        ConversationSequence or None.
    """
    result = await session.execute(
        select(ConversationSequence)
        .where(ConversationSequence.id == conversation_id)
        .options(selectinload(ConversationSequence.prompts))
    )
    return result.scalar_one_or_none()
