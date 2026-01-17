"""
Celery application configuration.
"""

from celery import Celery

from shared.config import settings

celery_app = Celery(
    "llm_brand_monitor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "services.scraper.app.tasks",
        "services.simulator.app.tasks",
        "services.classifier.app.tasks",
        "services.analyzer.app.tasks",
        "services.graph_builder.app.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Result backend
    result_expires=3600,  # 1 hour
    # Task routing
    task_routes={
        "services.scraper.app.tasks.*": {"queue": "scraping"},
        "services.simulator.app.tasks.*": {"queue": "simulation"},
        "services.classifier.app.tasks.*": {"queue": "classification"},
        "services.analyzer.app.tasks.*": {"queue": "analysis"},
        "services.graph_builder.app.tasks.*": {"queue": "graph"},
    },
    # Default queue
    task_default_queue="default",
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-cache": {
        "task": "services.api.app.tasks.cleanup_expired_cache",
        "schedule": 3600.0,  # Every hour
    },
    "update-share-of-voice-metrics": {
        "task": "services.analyzer.app.tasks.update_sov_metrics",
        "schedule": 86400.0,  # Every 24 hours
    },
}
