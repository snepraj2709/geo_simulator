"""
Celery tasks for classification and ICP generation.
"""

from celery import shared_task

from shared.queue.celery_app import celery_app
from shared.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="services.classifier.app.tasks.generate_icps")
def generate_icps(self, website_id: str):
    """
    Generate ICPs for a website.

    Args:
        website_id: UUID of the website.
    """
    logger.info("Generating ICPs", website_id=website_id)

    try:
        # TODO: Implement ICP generation
        # 1. Fetch website analysis
        # 2. Use LLM to generate 5 ICPs
        # 3. Store ICPs in database
        # 4. Trigger conversation generation

        logger.info("ICPs generated", website_id=website_id)

        # Trigger conversation generation
        celery_app.send_task(
            "services.classifier.app.tasks.generate_conversations",
            args=[website_id],
            queue="classification",
        )

        return {"status": "completed", "website_id": website_id}

    except Exception as e:
        logger.error(
            "ICP generation failed",
            website_id=website_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, name="services.classifier.app.tasks.generate_conversations")
def generate_conversations(self, website_id: str):
    """
    Generate conversation sequences for all ICPs.

    Args:
        website_id: UUID of the website.
    """
    logger.info("Generating conversations", website_id=website_id)

    try:
        # TODO: Implement conversation generation
        # 1. Fetch ICPs for website
        # 2. For each ICP, generate 10 conversations
        # 3. Mark 5 as core conversations
        # 4. Store in database
        # 5. Trigger prompt classification

        logger.info("Conversations generated", website_id=website_id)

        # Trigger prompt classification
        celery_app.send_task(
            "services.classifier.app.tasks.classify_prompts",
            args=[website_id],
            queue="classification",
        )

        return {"status": "completed", "website_id": website_id}

    except Exception as e:
        logger.error(
            "Conversation generation failed",
            website_id=website_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(name="services.classifier.app.tasks.classify_prompts")
def classify_prompts(website_id: str):
    """
    Classify all prompts for a website.

    Args:
        website_id: UUID of the website.
    """
    logger.info("Classifying prompts", website_id=website_id)

    # TODO: Implement prompt classification
    # 1. Fetch all prompts for website
    # 2. Classify each with intent, funnel stage, buying signal, trust need
    # 3. Store classifications

    return {"status": "completed", "website_id": website_id}
