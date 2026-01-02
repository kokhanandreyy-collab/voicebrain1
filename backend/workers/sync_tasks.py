from asgiref.sync import async_to_sync
from app.celery_app import celery
from app.infrastructure.database import AsyncSessionLocal
from app.core.sync_service import sync_service

async def _process_sync_async(note_id: str) -> None:
    from app.core.pipeline import pipeline
    await pipeline.process(note_id)

@celery.task(name="sync.process_note")
def process_sync(note_id: str):
    async_to_sync(_process_sync_async)(note_id)
    return {"status": "sync_restarted", "note_id": note_id}

# Individual Sync Wrappers (called by SyncService iteration)

async def _perform_sync_wrapper(note_id: str, provider: str, method_name: str = "perform_sync"):
    async with AsyncSessionLocal() as db:
        method = getattr(sync_service, method_name)
        # perform_sync takes (note_id, provider, db)
        # specialized ones like perform_sync_readwise take (note_id, db)
        if method_name == "perform_sync":
             await method(note_id, provider, db)
        elif method_name in ["perform_sync_tasks", "perform_sync_email", "perform_sync_maps"]:
             await method(note_id, provider, db)
        else:
             await method(note_id, db)

@celery.task(name="sync.google_maps")
def sync_google_maps(note_id: str):
    async_to_sync(_perform_sync_wrapper)(note_id, "google_maps", "perform_sync_maps")
    return {"status": "synced_google_maps", "note_id": note_id}

@celery.task(name="sync.yandex_maps")
def sync_yandex_maps(note_id: str):
    async_to_sync(_perform_sync_wrapper)(note_id, "yandex_maps", "perform_sync_maps")
    return {"status": "synced_yandex_maps", "note_id": note_id}

@celery.task(name="sync.tasks")
def sync_tasks(note_id: str, provider: str):
    async_to_sync(_perform_sync_wrapper)(note_id, provider, "perform_sync_tasks")
    return {"status": "synced_tasks", "provider": provider, "note_id": note_id}

@celery.task(name="sync.email")
def sync_email(note_id: str, provider: str):
    async_to_sync(_perform_sync_wrapper)(note_id, provider, "perform_sync_email")
    return {"status": "synced_email", "provider": provider, "note_id": note_id}

@celery.task(name="sync.readwise")
def sync_readwise(note_id: str):
    async_to_sync(_perform_sync_wrapper)(note_id, None, "perform_sync_readwise")
    return {"status": "synced_readwise", "note_id": note_id}

@celery.task(name="sync.obsidian")
def sync_obsidian(note_id: str):
    async_to_sync(_perform_sync_wrapper)(note_id, None, "perform_sync_obsidian")
    return {"status": "synced_obsidian", "note_id": note_id}

@celery.task(name="sync.yandex_tasks")
def sync_yandex_tasks(note_id: str):
    async_to_sync(_perform_sync_wrapper)(note_id, None, "perform_sync_yandex_tasks")
    return {"status": "synced_yandex_tasks", "note_id": note_id}

@celery.task(name="sync.maps")
def sync_maps(note_id: str, provider: str):
    async_to_sync(_perform_sync_wrapper)(note_id, provider, "perform_sync_maps")
    return {"status": "synced_maps", "provider": provider, "note_id": note_id}
