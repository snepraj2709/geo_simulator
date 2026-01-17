"""
Prompt Classifier Engine.

Classifies prompts with intent metadata for accurate simulation targeting.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.llm import LLMClient, LLMProvider, get_llm_client
from shared.models.conversation import ConversationSequence, Prompt, PromptClassification
from shared.models.icp import ICP
from shared.models.website import Website

from services.classifier.schemas import (
    ClassificationResult,
    PromptClassificationInput,
    PromptClassificationOutput,
    BatchClassificationOutput,
    LLMClassificationResponse,
    ClassificationSummary,
    ClassifiedPromptResponse,
    IntentType,
    FunnelStage,
    QueryIntent,
)
from services.classifier.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_single_classification_prompt,
    build_batch_classification_prompt,
    heuristic_classification,
)

logger = logging.getLogger(__name__)

CLASSIFIER_VERSION = "1.0.0"


class ClassificationError(Exception):
    """Error during prompt classification."""
    pass


class PromptClassifier:
    """
    Classifies prompts with intent metadata using LLM analysis.

    Features:
    - Classifies all 50 prompts per website
    - Supports batch and individual classification
    - Uses LLM for accurate intent analysis
    - Falls back to heuristic classification if LLM fails
    """

    MAX_RETRIES = 3
    DEFAULT_TEMPERATURE = 0.2  # Low for consistent classification
    BATCH_SIZE = 10  # Number of prompts to classify in one LLM call

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        llm_provider: LLMProvider | str = LLMProvider.OPENAI,
        use_heuristics_fallback: bool = True,
    ):
        """
        Initialize Prompt Classifier.

        Args:
            llm_client: Pre-configured LLM client (optional).
            llm_provider: LLM provider to use if client not provided.
            use_heuristics_fallback: Whether to fall back to heuristics on LLM failure.
        """
        if llm_client:
            self._client = llm_client
        else:
            self._client = get_llm_client(llm_provider)

        self._use_heuristics = use_heuristics_fallback

    async def classify_website_prompts(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
        force_reclassify: bool = False,
        icp_ids: list[uuid.UUID] | None = None,
    ) -> list[PromptClassification]:
        """
        Classify all prompts for a website.

        Args:
            website_id: UUID of the website.
            session: Database session.
            force_reclassify: Whether to reclassify already classified prompts.
            icp_ids: Optional filter for specific ICPs.

        Returns:
            List of PromptClassification objects.

        Raises:
            ClassificationError: If classification fails.
        """
        # Get all prompts for the website
        prompts = await self._get_website_prompts(
            website_id=website_id,
            session=session,
            icp_ids=icp_ids,
        )

        if not prompts:
            logger.warning("No prompts found for website %s", website_id)
            return []

        logger.info(
            "Classifying %d prompts for website %s",
            len(prompts),
            website_id,
        )

        # Filter out already classified prompts if not forcing reclassification
        if not force_reclassify:
            prompts = [p for p in prompts if not p.classification]
            if not prompts:
                logger.info("All prompts already classified for website %s", website_id)
                return await self._get_existing_classifications(website_id, session)

        # Classify in batches
        classifications = []
        for i in range(0, len(prompts), self.BATCH_SIZE):
            batch = prompts[i : i + self.BATCH_SIZE]
            batch_classifications = await self._classify_batch(batch, session)
            classifications.extend(batch_classifications)

            logger.info(
                "Classified batch %d-%d of %d prompts",
                i + 1,
                min(i + self.BATCH_SIZE, len(prompts)),
                len(prompts),
            )

        return classifications

    async def classify_single_prompt(
        self,
        prompt: Prompt,
        session: AsyncSession,
        conversation: ConversationSequence | None = None,
        icp: ICP | None = None,
    ) -> PromptClassification:
        """
        Classify a single prompt.

        Args:
            prompt: The prompt to classify.
            session: Database session.
            conversation: Optional conversation context.
            icp: Optional ICP context.

        Returns:
            PromptClassification object.
        """
        # Build classification input
        input_data = PromptClassificationInput(
            prompt_id=prompt.id,
            prompt_text=prompt.prompt_text,
            conversation_topic=conversation.topic if conversation else None,
            conversation_context=conversation.context if conversation else None,
            icp_name=icp.name if icp else None,
            icp_pain_points=icp.pain_points if icp else None,
        )

        # Classify
        result = await self._classify_with_llm(input_data)

        # Store classification
        classification = await self._store_classification(
            prompt_id=prompt.id,
            result=result,
            session=session,
        )

        return classification

    async def _classify_batch(
        self,
        prompts: list[Prompt],
        session: AsyncSession,
    ) -> list[PromptClassification]:
        """
        Classify a batch of prompts.

        Args:
            prompts: List of prompts to classify.
            session: Database session.

        Returns:
            List of PromptClassification objects.
        """
        # Build batch input
        batch_inputs = []
        for prompt in prompts:
            # Get conversation context if loaded
            conversation = prompt.conversation if hasattr(prompt, "conversation") else None

            batch_inputs.append({
                "prompt_id": str(prompt.id),
                "prompt_text": prompt.prompt_text,
                "context": conversation.topic if conversation else None,
            })

        # Try LLM classification
        try:
            results = await self._classify_batch_with_llm(batch_inputs)
        except Exception as e:
            logger.warning("LLM batch classification failed: %s", e)
            if self._use_heuristics:
                results = self._classify_batch_with_heuristics(batch_inputs)
            else:
                raise ClassificationError(f"Batch classification failed: {e}")

        # Store classifications
        classifications = []
        for prompt, result in zip(prompts, results):
            try:
                classification = await self._store_classification(
                    prompt_id=prompt.id,
                    result=result,
                    session=session,
                )
                classifications.append(classification)
            except Exception as e:
                logger.error("Failed to store classification for prompt %s: %s", prompt.id, e)

        return classifications

    async def _classify_with_llm(
        self,
        input_data: PromptClassificationInput,
    ) -> ClassificationResult:
        """
        Classify a single prompt using LLM.

        Args:
            input_data: Classification input.

        Returns:
            ClassificationResult.

        Raises:
            ClassificationError: If classification fails.
        """
        prompt = build_single_classification_prompt(
            prompt_text=input_data.prompt_text,
            conversation_topic=input_data.conversation_topic,
            conversation_context=input_data.conversation_context,
            icp_name=input_data.icp_name,
            icp_pain_points=input_data.icp_pain_points,
        )

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.complete_json(
                    prompt=prompt,
                    system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                    temperature=self.DEFAULT_TEMPERATURE,
                    max_tokens=500,
                )

                if not response.success:
                    raise ClassificationError("LLM returned empty response")

                parsed = LLMClassificationResponse.model_validate(response.get_json())
                return parsed.to_classification_result()

            except ValidationError as e:
                logger.warning(
                    "Classification validation failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:200],
                )
            except Exception as e:
                logger.warning(
                    "Classification failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:200],
                )

        # Fall back to heuristics
        if self._use_heuristics:
            logger.info("Falling back to heuristic classification")
            heuristic_result = heuristic_classification(input_data.prompt_text)
            return ClassificationResult(
                intent_type=IntentType(heuristic_result["intent_type"]),
                funnel_stage=FunnelStage(heuristic_result["funnel_stage"]),
                buying_signal=heuristic_result["buying_signal"],
                trust_need=heuristic_result["trust_need"],
                query_intent=QueryIntent(heuristic_result["query_intent"]) if heuristic_result.get("query_intent") else None,
                confidence_score=0.5,  # Lower confidence for heuristics
                reasoning=heuristic_result["reasoning"],
            )

        raise ClassificationError("Failed to classify prompt after max retries")

    async def _classify_batch_with_llm(
        self,
        batch_inputs: list[dict],
    ) -> list[ClassificationResult]:
        """
        Classify multiple prompts using LLM.

        Args:
            batch_inputs: List of prompt inputs.

        Returns:
            List of ClassificationResult objects.
        """
        prompt = build_batch_classification_prompt(batch_inputs)

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self._client.complete_json(
                    prompt=prompt,
                    system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
                    temperature=self.DEFAULT_TEMPERATURE,
                    max_tokens=2000,
                )

                if not response.success:
                    raise ClassificationError("LLM returned empty response")

                raw_json = response.get_json()

                # Handle both direct array and wrapped response
                if isinstance(raw_json, dict) and "classifications" in raw_json:
                    classifications_data = raw_json["classifications"]
                elif isinstance(raw_json, list):
                    classifications_data = raw_json
                else:
                    raise ClassificationError("Invalid response format")

                if len(classifications_data) != len(batch_inputs):
                    logger.warning(
                        "Classification count mismatch: expected %d, got %d",
                        len(batch_inputs),
                        len(classifications_data),
                    )

                results = []
                for data in classifications_data:
                    parsed = LLMClassificationResponse.model_validate(data)
                    results.append(parsed.to_classification_result())

                # Pad with heuristics if we got fewer results
                while len(results) < len(batch_inputs):
                    idx = len(results)
                    heuristic_result = heuristic_classification(batch_inputs[idx]["prompt_text"])
                    results.append(ClassificationResult(
                        intent_type=IntentType(heuristic_result["intent_type"]),
                        funnel_stage=FunnelStage(heuristic_result["funnel_stage"]),
                        buying_signal=heuristic_result["buying_signal"],
                        trust_need=heuristic_result["trust_need"],
                        query_intent=QueryIntent(heuristic_result["query_intent"]) if heuristic_result.get("query_intent") else None,
                        confidence_score=0.5,
                        reasoning="Heuristic fallback",
                    ))

                return results

            except ValidationError as e:
                logger.warning(
                    "Batch classification validation failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:200],
                )
            except Exception as e:
                logger.warning(
                    "Batch classification failed on attempt %d: %s",
                    attempt + 1,
                    str(e)[:200],
                )

        # Fall back to heuristics
        if self._use_heuristics:
            return self._classify_batch_with_heuristics(batch_inputs)

        raise ClassificationError("Failed to classify batch after max retries")

    def _classify_batch_with_heuristics(
        self,
        batch_inputs: list[dict],
    ) -> list[ClassificationResult]:
        """
        Classify batch using heuristics as fallback.

        Args:
            batch_inputs: List of prompt inputs.

        Returns:
            List of ClassificationResult objects.
        """
        results = []
        for input_data in batch_inputs:
            heuristic_result = heuristic_classification(input_data["prompt_text"])
            results.append(ClassificationResult(
                intent_type=IntentType(heuristic_result["intent_type"]),
                funnel_stage=FunnelStage(heuristic_result["funnel_stage"]),
                buying_signal=heuristic_result["buying_signal"],
                trust_need=heuristic_result["trust_need"],
                query_intent=QueryIntent(heuristic_result["query_intent"]) if heuristic_result.get("query_intent") else None,
                confidence_score=0.5,
                reasoning=heuristic_result["reasoning"],
            ))
        return results

    async def _store_classification(
        self,
        prompt_id: uuid.UUID,
        result: ClassificationResult,
        session: AsyncSession,
    ) -> PromptClassification:
        """
        Store classification in the database.

        Args:
            prompt_id: The prompt ID.
            result: Classification result.
            session: Database session.

        Returns:
            Stored PromptClassification object.
        """
        # Check for existing classification
        existing = await session.execute(
            select(PromptClassification).where(
                PromptClassification.prompt_id == prompt_id
            )
        )
        classification = existing.scalar_one_or_none()

        if classification:
            # Update existing
            classification.intent_type = result.intent_type
            classification.funnel_stage = result.funnel_stage
            classification.buying_signal = Decimal(str(result.buying_signal))
            classification.trust_need = Decimal(str(result.trust_need))
            classification.query_intent = result.query_intent if result.query_intent else None
            classification.confidence_score = Decimal(str(result.confidence_score))
            classification.classified_at = datetime.now(timezone.utc)
            classification.classifier_version = CLASSIFIER_VERSION
        else:
            # Create new
            classification = PromptClassification(
                id=uuid.uuid4(),
                prompt_id=prompt_id,
                intent_type=result.intent_type,
                funnel_stage=result.funnel_stage,
                buying_signal=Decimal(str(result.buying_signal)),
                trust_need=Decimal(str(result.trust_need)),
                query_intent=result.query_intent if result.query_intent else None,
                confidence_score=Decimal(str(result.confidence_score)),
                classified_at=datetime.now(timezone.utc),
                classifier_version=CLASSIFIER_VERSION,
            )
            session.add(classification)

        await session.commit()
        await session.refresh(classification)

        return classification

    async def _get_website_prompts(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
        icp_ids: list[uuid.UUID] | None = None,
    ) -> list[Prompt]:
        """
        Get all prompts for a website.

        Args:
            website_id: Website UUID.
            session: Database session.
            icp_ids: Optional filter for specific ICPs.

        Returns:
            List of Prompt objects.
        """
        # Build query
        query = (
            select(Prompt)
            .join(ConversationSequence)
            .where(ConversationSequence.website_id == website_id)
            .options(
                selectinload(Prompt.conversation),
                selectinload(Prompt.classification),
            )
        )

        if icp_ids:
            query = query.where(ConversationSequence.icp_id.in_(icp_ids))

        result = await session.execute(query)
        return list(result.scalars().all())

    async def _get_existing_classifications(
        self,
        website_id: uuid.UUID,
        session: AsyncSession,
    ) -> list[PromptClassification]:
        """
        Get existing classifications for a website.

        Args:
            website_id: Website UUID.
            session: Database session.

        Returns:
            List of PromptClassification objects.
        """
        result = await session.execute(
            select(PromptClassification)
            .join(Prompt)
            .join(ConversationSequence)
            .where(ConversationSequence.website_id == website_id)
        )
        return list(result.scalars().all())


# ==================== Utility Functions ====================


async def get_classifications_for_website(
    website_id: uuid.UUID,
    session: AsyncSession,
    intent_type: str | None = None,
    funnel_stage: str | None = None,
    min_buying_signal: float | None = None,
    min_trust_need: float | None = None,
) -> tuple[list[ClassifiedPromptResponse], ClassificationSummary]:
    """
    Get all classifications for a website with filters.

    Args:
        website_id: Website UUID.
        session: Database session.
        intent_type: Filter by intent type.
        funnel_stage: Filter by funnel stage.
        min_buying_signal: Minimum buying signal.
        min_trust_need: Minimum trust need.

    Returns:
        Tuple of (classifications list, summary).
    """
    # Build query with filters
    query = (
        select(PromptClassification, Prompt, ConversationSequence)
        .join(Prompt, PromptClassification.prompt_id == Prompt.id)
        .join(ConversationSequence, Prompt.conversation_id == ConversationSequence.id)
        .where(ConversationSequence.website_id == website_id)
    )

    if intent_type:
        query = query.where(PromptClassification.intent_type == intent_type)
    if funnel_stage:
        query = query.where(PromptClassification.funnel_stage == funnel_stage)
    if min_buying_signal is not None:
        query = query.where(PromptClassification.buying_signal >= Decimal(str(min_buying_signal)))
    if min_trust_need is not None:
        query = query.where(PromptClassification.trust_need >= Decimal(str(min_trust_need)))

    result = await session.execute(query)
    rows = result.all()

    # Build response list
    classifications = []
    for classification, prompt, conversation in rows:
        classifications.append(ClassifiedPromptResponse(
            prompt_id=prompt.id,
            prompt_text=prompt.prompt_text,
            conversation_id=conversation.id,
            icp_id=conversation.icp_id,
            classification=ClassificationResult(
                intent_type=IntentType(classification.intent_type),
                funnel_stage=FunnelStage(classification.funnel_stage),
                buying_signal=float(classification.buying_signal),
                trust_need=float(classification.trust_need),
                query_intent=QueryIntent(classification.query_intent) if classification.query_intent else None,
                confidence_score=float(classification.confidence_score) if classification.confidence_score else 0.0,
            ),
            classified_at=classification.classified_at,
        ))

    # Build summary
    summary = _build_classification_summary(classifications)

    return classifications, summary


def _build_classification_summary(
    classifications: list[ClassifiedPromptResponse],
) -> ClassificationSummary:
    """Build summary statistics from classifications."""
    if not classifications:
        return ClassificationSummary(
            total=0,
            by_intent_type={},
            by_funnel_stage={},
            by_query_intent={},
            avg_buying_signal=0.0,
            avg_trust_need=0.0,
        )

    # Count by dimensions
    by_intent_type = {}
    by_funnel_stage = {}
    by_query_intent = {}
    total_buying_signal = 0.0
    total_trust_need = 0.0

    for c in classifications:
        # Intent type
        intent = c.classification.intent_type
        by_intent_type[intent] = by_intent_type.get(intent, 0) + 1

        # Funnel stage
        stage = c.classification.funnel_stage
        by_funnel_stage[stage] = by_funnel_stage.get(stage, 0) + 1

        # Query intent
        qi = c.classification.query_intent
        if qi:
            by_query_intent[qi] = by_query_intent.get(qi, 0) + 1

        # Scores
        total_buying_signal += c.classification.buying_signal
        total_trust_need += c.classification.trust_need

    total = len(classifications)

    return ClassificationSummary(
        total=total,
        by_intent_type=by_intent_type,
        by_funnel_stage=by_funnel_stage,
        by_query_intent=by_query_intent,
        avg_buying_signal=round(total_buying_signal / total, 3) if total else 0.0,
        avg_trust_need=round(total_trust_need / total, 3) if total else 0.0,
    )
