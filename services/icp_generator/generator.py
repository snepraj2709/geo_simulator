"""
ICP Generator service.

Generates Ideal Customer Profiles using LLM analysis of website content.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.llm import LLMClient, LLMProvider, get_llm_client, ResponseFormat
from shared.models.icp import ICP
from shared.models.website import Website, WebsiteAnalysis, ScrapedPage

from services.icp_generator.schemas import (
    ICPGenerationResponse,
    GeneratedICP,
    WebsiteContext,
)
from services.icp_generator.prompts import (
    ICP_SYSTEM_PROMPT,
    build_icp_generation_prompt,
    build_minimal_context_prompt,
)

logger = logging.getLogger(__name__)


class ICPGenerationError(Exception):
    """Error during ICP generation."""
    pass


class ICPGenerator:
    """
    Generates Ideal Customer Profiles for websites using LLM.

    Features:
    - Analyzes scraped website content
    - Generates exactly 5 diverse ICPs
    - Validates and ensures uniqueness
    - Supports multiple LLM providers
    """

    MAX_RETRIES = 3
    DEFAULT_TEMPERATURE = 0.4  # Lower for more consistent JSON output

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        llm_provider: LLMProvider | str = LLMProvider.OPENAI,
    ):
        """
        Initialize ICP Generator.

        Args:
            llm_client: Pre-configured LLM client (optional).
            llm_provider: LLM provider to use if client not provided.
        """
        if llm_client:
            self._client = llm_client
        else:
            self._client = get_llm_client(llm_provider)

    async def generate_icps(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
        force_regenerate: bool = False,
    ) -> list[ICP]:
        """
        Generate ICPs for a website.

        Args:
            website_id: UUID of the website.
            session: Database session.
            force_regenerate: Whether to regenerate if ICPs exist.

        Returns:
            List of generated ICP models.

        Raises:
            ICPGenerationError: If generation fails.
        """
        # Check for existing ICPs
        if not force_regenerate:
            existing = await self._get_existing_icps(website_id, session)
            if existing:
                logger.info("Using existing ICPs for website %s", website_id)
                return existing

        # Get website context
        context = await self._build_context(website_id, session)
        if not context:
            raise ICPGenerationError(f"Website not found: {website_id}")

        logger.info("Generating ICPs for website %s (%s)", website_id, context.domain)

        # Generate ICPs with retries
        generated_icps = await self._generate_with_retries(context)

        # Delete existing ICPs if regenerating
        if force_regenerate:
            await self._delete_existing_icps(website_id, session)

        # Store in database
        stored_icps = await self._store_icps(website_id, generated_icps, session)

        logger.info("Successfully generated %d ICPs for website %s", len(stored_icps), website_id)
        return stored_icps

    async def _generate_with_retries(
        self,
        context: WebsiteContext,
    ) -> list[GeneratedICP]:
        """
        Generate ICPs with retry logic.

        Args:
            context: Website context for generation.

        Returns:
            List of validated GeneratedICP objects.

        Raises:
            ICPGenerationError: If all retries fail.
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Build prompt
                if context.scraped_content_summary or context.primary_offerings:
                    prompt = build_icp_generation_prompt(context)
                else:
                    prompt = build_minimal_context_prompt(
                        domain=context.domain,
                        name=context.name,
                        industry=context.industry,
                    )

                # Call LLM
                response = await self._client.complete_json(
                    prompt=prompt,
                    system_prompt=ICP_SYSTEM_PROMPT,
                    temperature=self.DEFAULT_TEMPERATURE,
                    max_tokens=8000,
                )

                if not response.success:
                    raise ICPGenerationError("LLM returned empty response")

                # Parse and validate
                parsed = response.parse_as(ICPGenerationResponse)

                # Validate diversity
                self._validate_diversity(parsed.icps)

                logger.info(
                    "ICP generation succeeded on attempt %d (tokens: %d, latency: %dms)",
                    attempt + 1,
                    response.tokens_used,
                    response.latency_ms,
                )

                return parsed.icps

            except ValidationError as e:
                last_error = e
                logger.warning(
                    "ICP validation failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:200],
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "ICP generation failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:200],
                )

        raise ICPGenerationError(
            f"Failed to generate valid ICPs after {self.MAX_RETRIES} attempts: {last_error}"
        )

    def _validate_diversity(self, icps: list[GeneratedICP]) -> None:
        """
        Validate that ICPs are sufficiently diverse.

        Args:
            icps: List of generated ICPs.

        Raises:
            ValueError: If ICPs lack diversity.
        """
        if len(icps) != 5:
            raise ValueError(f"Expected 5 ICPs, got {len(icps)}")

        # Check unique names
        names = [icp.name.lower().strip() for icp in icps]
        if len(set(names)) != 5:
            raise ValueError("ICP names must be unique")

        # Check for some diversity in company sizes
        company_sizes = set(
            icp.professional_profile.company_size for icp in icps
        )
        if len(company_sizes) < 2:
            logger.warning("Limited diversity in company sizes: %s", company_sizes)

        # Check for diversity in seniority
        seniority_levels = set(
            icp.professional_profile.seniority_level for icp in icps
        )
        if len(seniority_levels) < 2:
            logger.warning("Limited diversity in seniority levels: %s", seniority_levels)

        # Check for diversity in buying journey stages
        stages = set(icp.buying_journey_stage for icp in icps)
        if len(stages) < 2:
            logger.warning("Limited diversity in buying journey stages: %s", stages)

    async def _build_context(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
    ) -> WebsiteContext | None:
        """
        Build website context for ICP generation.

        Args:
            website_id: Website UUID.
            session: Database session.

        Returns:
            WebsiteContext or None if website not found.
        """
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

        # Get content summary from scraped pages
        pages_result = await session.execute(
            select(ScrapedPage)
            .where(ScrapedPage.website_id == website_id)
            .order_by(ScrapedPage.word_count.desc())
            .limit(5)
        )
        pages = pages_result.scalars().all()

        content_summary = None
        if pages:
            summaries = []
            for page in pages:
                if page.content_text:
                    # Take first 500 chars of each page
                    text = page.content_text[:500]
                    if page.title:
                        summaries.append(f"[{page.title}] {text}")
                    else:
                        summaries.append(text)
            if summaries:
                content_summary = "\n\n".join(summaries)

        return WebsiteContext(
            domain=website.domain,
            name=website.name,
            description=website.description,
            industry=analysis.industry if analysis else None,
            business_model=analysis.business_model if analysis else None,
            primary_offerings=analysis.primary_offerings if analysis else None,
            value_propositions=analysis.value_propositions if analysis else None,
            target_markets=analysis.target_markets if analysis else None,
            company_profile=analysis.company_profile if analysis else None,
            products_detailed=analysis.products_detailed if analysis else None,
            services_detailed=analysis.services_detailed if analysis else None,
            target_audience=analysis.target_audience if analysis else None,
            scraped_content_summary=content_summary,
        )

    async def _get_existing_icps(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[ICP]:
        """Get existing ICPs for a website."""
        result = await session.execute(
            select(ICP)
            .where(ICP.website_id == website_id)
            .order_by(ICP.sequence_number)
        )
        return list(result.scalars().all())

    async def _delete_existing_icps(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
    ) -> int:
        """Delete existing ICPs for a website."""
        result = await session.execute(
            delete(ICP).where(ICP.website_id == website_id)
        )
        await session.commit()
        return result.rowcount

    async def _store_icps(
        self,
        website_id: uuid.UUID,
        generated_icps: list[GeneratedICP],
        session: AsyncSession,
    ) -> list[ICP]:
        """
        Store generated ICPs in the database.

        Args:
            website_id: Website UUID.
            generated_icps: List of generated ICPs.
            session: Database session.

        Returns:
            List of stored ICP models.
        """
        stored = []

        for i, gen_icp in enumerate(generated_icps, start=1):
            icp = ICP(
                id=uuid.uuid4(),
                website_id=website_id,
                name=gen_icp.name,
                description=gen_icp.description,
                sequence_number=i,
                demographics=gen_icp.demographics.model_dump(),
                professional_profile=gen_icp.professional_profile.model_dump(),
                pain_points=gen_icp.pain_points,
                goals=gen_icp.goals,
                motivations=gen_icp.motivations.model_dump(),
                objections=gen_icp.objections,
                decision_factors=gen_icp.decision_factors,
                information_sources=gen_icp.information_sources,
                buying_journey_stage=gen_icp.buying_journey_stage.value,
                is_active=True,
            )
            session.add(icp)
            stored.append(icp)

        await session.commit()

        # Refresh to get generated timestamps
        for icp in stored:
            await session.refresh(icp)

        return stored


async def get_icps_for_website(
    website_id: uuid.UUID,
    session: AsyncSession,
    active_only: bool = True,
) -> list[ICP]:
    """
    Get ICPs for a website.

    Args:
        website_id: Website UUID.
        session: Database session.
        active_only: Whether to return only active ICPs.

    Returns:
        List of ICP models.
    """
    query = select(ICP).where(ICP.website_id == website_id)

    if active_only:
        query = query.where(ICP.is_active == True)

    query = query.order_by(ICP.sequence_number)

    result = await session.execute(query)
    return list(result.scalars().all())
