from infrastructure.config import settings

broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

celery = Celery(
    "voicebrain_worker",
    broker=broker_url,
    backend=result_backend,
    include=[
        "workers.transcribe_tasks",
        "workers.analyze_tasks",
        "workers.sync_tasks",
        "workers.maintenance_tasks",
        "workers.reflection_tasks"
    ]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="celery",
    task_routes={
        "transcribe.*": {"queue": "transcribe_queue"},
        "analyze.*": {"queue": "analyze_queue"},
        "sync.*": {"queue": "sync_queue"},
    }
)

from celery.schedules import crontab

celery.conf.beat_schedule = {
    # Cleanup old notes daily at 2:30 AM
    "cleanup-old-notes-every-day": {
        "task": "cleanup_old_notes",
        "schedule": crontab(hour=2, minute=30),
    },
    "generate-weekly-review": {
        "task": "generate_weekly_review",
        "schedule": crontab(hour=18, minute=0, day_of_week=0),
    },
    "check-subscriptions-daily": {
        "task": "check_subscription_expiry",
        "schedule": crontab(hour=9, minute=0),
    },
    "backup-database-daily": {
        "task": "backup_database",
        "schedule": crontab(hour=4, minute=0),
    },
    "daily-reflection-trigger": {
        "task": "reflection.trigger_daily",
        "schedule": crontab(hour=1, minute=0), # Run at 1:00 AM
    }
}
