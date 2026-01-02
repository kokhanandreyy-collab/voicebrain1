from asgiref.sync import async_to_sync
from app.celery_app import celery

async def _process_analyze_async(note_id: str) -> None:
    from app.services.pipeline import pipeline
    await pipeline.process(note_id)

@celery.task(name="analyze.process_note")
def process_analyze(note_id: str):
    async_to_sync(_process_analyze_async)(note_id)
    return {"status": "analysis_restarted", "note_id": note_id}
