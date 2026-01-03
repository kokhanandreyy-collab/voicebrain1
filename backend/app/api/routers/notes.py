from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, update
from typing import List

from infrastructure.database import get_db
from app.models import User, Note, TIER_LIMITS, Integration, IntegrationLog
from app.schemas import NoteResponse, NoteUpdate, AskRequest, AskResponse, RelatedNote
from pydantic import BaseModel
from app.services.ai_service import ai_service
from app.api.dependencies import get_current_user
from typing import Optional
from datetime import datetime, timezone
from fastapi_limiter.depends import RateLimiter
from infrastructure.config import settings

router = APIRouter()

from infrastructure.storage import storage_client
import uuid

@router.post("/upload", response_model=NoteResponse)
async def upload_note(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Manual Rate Limiting for Tier-based logic (simpler than hacking Depends check)
    # Check limit key in Redis: "limit:upload:{user_id}"
    from fastapi_limiter import FastAPILimiter
    import redis.asyncio as redis
    
    # 10/hr (Free), 50/hr (Pro)
    limit = 10 if current_user.tier == "free" else 50
    key = f"limit/upload/{current_user.id}"
    
    redis_conn = FastAPILimiter.redis
    # Provide a fallback if redis not connected
    if redis_conn:
        try:
             # p_expire is ms
             # incr returns the new value
             current_usage = await redis_conn.incr(key)
             if current_usage == 1:
                 await redis_conn.expire(key, 3600)
             
             if current_usage > limit:
                 ttl = await redis_conn.ttl(key)
                 raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {ttl} seconds.")
        except Exception as e:
             # If redis fails, we log and allow (fail open) or block
             print(f"Rate limit check failed: {e}")
    
    # ... existing code ...
    # 1. Stream to Temp File
    import shutil
    import tempfile
    import os # Keep os for file operations like close/remove
    
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else "webm"
    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=f".{file_ext}")
    os.close(fd)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_size = os.path.getsize(temp_path)
    duration_est = max(1, file_size // 16000) 
    
    # LIMIT CHECK
    current_tier_limits = TIER_LIMITS.get(current_user.tier, TIER_LIMITS["free"])
    monthly_limit = current_tier_limits["monthly_transcription_seconds"]
    
    # 1. Check for Reset
    now = datetime.now(timezone.utc) # Aware UTC
    # Using naive for simplicity here, assuming models return naive or we compare date parts only
    
    should_reset = False
    
    if not current_user.billing_cycle_start:
         current_user.billing_cycle_start = now
         should_reset = True
    
    if current_user.tier == "free":
        # Calendar month reset (1st of month)
        if current_user.billing_cycle_start.month != now.month or current_user.billing_cycle_start.year != now.year:
            should_reset = True
            # Update cycle start to start of this month roughly (or just now is fine, checks just month)
            current_user.billing_cycle_start = now 
    else:
        # Rolling 30 day window (or monthly from payment date)
        # If today > cycle_start + 30 days
        diff = now - current_user.billing_cycle_start.replace(tzinfo=None) # naive safety
        if diff.days >= 30:
             should_reset = True
             current_user.billing_cycle_start = now

    if should_reset:
        current_user.monthly_usage_seconds = 0
        db.add(current_user)

    if monthly_limit != float('inf'):
        if current_user.monthly_usage_seconds + duration_est > monthly_limit:
             if os.path.exists(temp_path):
                 os.remove(temp_path)
             raise HTTPException(
                 status_code=403, 
                 detail=f"Monthly transcription limit reached. You have {(monthly_limit - current_user.monthly_usage_seconds)//60} mins left."
             )

    # 2. Upload to Storage (S3)
    # file_ext calculated above
    file_key = f"{current_user.id}/{uuid.uuid4()}.{file_ext}"
    
    try:
        with open(temp_path, "rb") as f_in:
            audio_url = await storage_client.upload_file(f_in, file_key, content_type=file.content_type or "audio/webm")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
        
    # Cleanup Temp
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # 3. Create Note (Processing State)
    new_note = Note(
        user_id=current_user.id,
        audio_url=audio_url,
        storage_key=file_key,
        title="Processing...",
        status="PROCESSING",
        duration_seconds=duration_est,
        summary="Analysis in progress...",
        transcription_text="",
        processing_step="☁️ Uploading..."
    )
    db.add(new_note)
    
    # Update Usage (Atomic)
    # Update Usage & Streak
    # Fetch latest user state to be safe for streak calc
    # Actually current_user is passed by dependency, but let's just update fields directly and let commit handle it.
    
    # Streak Logic
    now = datetime.now(timezone.utc)
    today = now.date()
    last = current_user.last_note_date.date() if current_user.last_note_date else None
    
    if last != today:
        if last == today - timedelta(days=1):
            current_user.streak_days = (current_user.streak_days or 0) + 1
        else:
            current_user.streak_days = 1
            
    current_user.last_note_date = now
    
    # Update DB
    current_user.monthly_usage_seconds += duration_est
    # Note: If we just modified current_user object attached to session, db.commit() saves it.
    # The previous code used explicit update(User), which might bypass object state if not careful.
    # Since current_user is from get_current_user which uses GET, it is attached.
    # But get_current_user might detach? Default boilerplate attaches.
    # Let's trust session.add(current_user) or just commit.
    
    await db.commit()
    await db.refresh(new_note)

    # 4. Trigger Background Worker
    from workers.transcribe_tasks import process_transcribe
    try:
        # Check if Redis is available, otherwise run inline
        if settings.CELERY_BROKER_URL:
             process_transcribe.delay(new_note.id)
        else:
             print("[Warning] No Celery Broker. Running task synchronously.")
             process_transcribe(new_note.id) 
    except Exception as e:
        print(f"[Upload Error] Failed to queue task: {e}")

    

    return new_note

async def attach_integration_status(db: AsyncSession, notes: List[Note]):
    if not notes:
        return
    note_ids = [n.id for n in notes]
    result = await db.execute(
        select(IntegrationLog, Integration.provider)
        .join(Integration, IntegrationLog.integration_id == Integration.id)
        .where(IntegrationLog.note_id.in_(note_ids))
    )
    logs = result.all()
    status_map = {}
    for log, provider in logs:
        if log.note_id not in status_map:
            status_map[log.note_id] = []
        status_map[log.note_id].append({
            "provider": provider,
            "status": log.status,
            "timestamp": log.created_at,
            "error": log.error_message
        })
    for note in notes:
        note.integration_status = status_map.get(note.id, [])

@router.get("", response_model=List[NoteResponse])
async def get_notes(
    skip: int = 0, 
    limit: int = 100, 
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    query = select(Note).where(Note.user_id == current_user.id)
    
    if q:
        # Semantic Search (RAG)
        query_embedding = await ai_service.generate_embedding(q)
        # Order by cosine distance (nearest neighbors first)
        query = query.order_by(Note.embedding.cosine_distance(query_embedding))
    
    notes_res = await db.execute(query.limit(limit).offset(skip))
    notes = notes_res.scalars().all()
    await attach_integration_status(db, notes)
    return notes

@router.post("/ask", response_model=AskResponse, dependencies=[Depends(RateLimiter(times=20, seconds=3600))])
async def ask_ai(
    req: AskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Generate Embedding for Question
    question_embedding = await ai_service.generate_embedding(req.question)
    
    # 2. Hybrid Search
    # 2.1 Semantic Search (Vector)
    query_sem = select(Note).where(Note.user_id == current_user.id)
    query_sem = query_sem.order_by(Note.embedding.cosine_distance(question_embedding)).limit(10)
    
    result_sem = await db.execute(query_sem)
    semantic_notes = result_sem.scalars().all()
    
    # 2.2 Keyword Search (SQL ILIKE)
    # Simple keyword match on title or content
    # In a real system, you'd extract keywords from the question first.
    # Here we perform a loose match if the query is not too long to be helpful, 
    # or just match on specific terms if we had a keyword extractor.
    # For now, we search for the full phrase or fall back to semantic only if string is too generic.
    
    keyword_notes = []
    # Only try keyword search if it looks like a keyword query (short-ish) or specific phrase
    if len(req.question.split()) < 10:
         query_kw = select(Note).where(
             Note.user_id == current_user.id,
             or_(
                 Note.title.ilike(f"%{req.question}%"),
                 Note.summary.ilike(f"%{req.question}%"),
                 Note.transcription_text.ilike(f"%{req.question}%")
             )
         ).limit(10)
         result_kw = await db.execute(query_kw)
         keyword_notes = result_kw.scalars().all()

    # 2.3 Combine & Deduplicate (Rank Fusion - naive)
    combined_notes_map = {n.id: n for n in semantic_notes}
    for n in keyword_notes:
        combined_notes_map[n.id] = n # Overwrite/Add
        
    relevant_notes = list(combined_notes_map.values())
    
    if not relevant_notes:
         return {"answer": "You don't have any notes yet, so I can't answer that question."}
         
    # 3. Construct Context
    context_text = "\n\n".join([
        f"Note Title: {n.title}\n{n.summary or n.transcription_text[:500]}..." 
        for n in relevant_notes
    ])
    
    # 4. Generate Answer
    answer = await ai_service.ask_notes(context_text, req.question)
    
    return {"answer": answer}
    


@router.post("/search/voice", response_model=List[NoteResponse])
async def search_voice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Transcribe query
    content = await file.read()
    transcription = await ai_service.transcribe_audio(content)
    query_text = transcription["text"]
    
    print(f"Voice Search Query: {query_text}")
    
    # 2. Perform Semantic Search
    query_embedding = await ai_service.generate_embedding(query_text)
    
    result = await db.execute(
        select(Note)
        .where(Note.user_id == current_user.id)
        .order_by(Note.embedding.cosine_distance(query_embedding))
        .limit(20)
    )
    return result.scalars().all()

@router.post("/transcribe")
async def transcribe_audio_only(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Helper endpoint to transcribe audio and return text.
    Used for Voice Input in Search/Ask AI.
    """
    content = await file.read()
    transcription = await ai_service.transcribe_audio(content)
    return {"text": transcription["text"]}

@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_detail(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await attach_integration_status(db, [note])
    return note

@router.get("/{note_id}/related", response_model=List[RelatedNote])
async def get_related_notes(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch Source Note
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    source_note = result.scalars().first()
    if not source_note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    if not source_note.embedding_data:
         # No embedding, no semantic search
         return []
         
    # 2. Vector Search (Exclude source, distance < 0.25)
    # Cosine Distance: 0 = Identical
    threshold = 0.25
    
    query = (
        select(Note, Note.embedding.cosine_distance(source_note.embedding_data.embedding).label("distance"))
        .filter(Note.id != note_id)
        .filter(Note.user_id == current_user.id)
        .order_by("distance")
        .limit(3)
    )
    
    res = await db.execute(query)
    matches = res.all()
    
    related = []
    for note, distance in matches:
        if distance < threshold:
             related.append(RelatedNote(
                 id=note.id,
                 title=note.title or "Untitled",
                 summary=note.summary,
                 created_at=note.created_at,
                 similarity=1.0 - distance
             ))
             
    return related

@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Delete from S3
    if note.storage_key:
        await storage_client.delete_file(note.storage_key)
    elif note.audio_url:
        # Legacy fallback
        await storage_client.delete_file(note.audio_url)
    
    await db.delete(note)
    await db.commit()
    await db.delete(note)
    await db.commit()
    return None

class BatchDeleteRequest(BaseModel):
    note_ids: List[str]

@router.post("/batch/delete", status_code=204)
async def delete_notes_batch(
    req: BatchDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch all notes to verify ownership
    result = await db.execute(select(Note).where(Note.id.in_(req.note_ids), Note.user_id == current_user.id))
    notes = result.scalars().all()
    
    if not notes:
        return None
        
    for note in notes:
        # Delete from S3
        if note.storage_key:
            await storage_client.delete_file(note.storage_key)
        elif note.audio_url:
            await storage_client.delete_file(note.audio_url)
        
        await db.delete(note)
        
    await db.commit()
    return None

@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # Update fields
    needs_reembedding = False
    
    if note_update.title is not None:
        note.title = note_update.title
        needs_reembedding = True
    if note_update.summary is not None:
        note.summary = note_update.summary
        needs_reembedding = True
    if note_update.transcription_text is not None:
        note.transcription_text = note_update.transcription_text
        needs_reembedding = True
    if note_update.tags is not None:
        note.tags = note_update.tags
        needs_reembedding = True
    if note_update.mood is not None:
        note.mood = note_update.mood
        
    # Re-calculate embedding if semantic content changed
    if needs_reembedding:
        search_content = f"{note.title or ''} {note.summary or ''} {note.transcription_text or ''} {' '.join(note.tags or [])}"
        note.embedding = await ai_service.generate_embedding(search_content)
        
    await db.commit()
    await db.refresh(note)
    return note

@router.post("/{note_id}/extract-health")
async def extract_health(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Get Note
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    # 2. Extract
    # Use full text (transcription) for analysis
    text_to_analyze = note.transcription_text
    if not text_to_analyze:
        return {}
        
    metrics = await ai_service.extract_health_metrics(text_to_analyze, user_id=current_user.id, db=db)
    
    # Persist the findings
    if metrics:
        note.health_data = metrics
        await db.commit()
        await db.refresh(note)
        
    return metrics

@router.post("/{note_id}/share/{provider}")
async def share_note(
    note_id: str,
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Get Note
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # 2. Get Integration
    int_result = await db.execute(
        select(Integration).where(
            Integration.user_id == current_user.id, 
            Integration.provider == provider
        )
    )
    integration = int_result.scalars().first()
    
    # Pro Access Check
    if provider in ['notion', 'slack', 'microsoft_todo', 'ticktick', 'reflect', 'craft', 'google_keep'] and not current_user.is_pro:
         raise HTTPException(status_code=403, detail=f"Sharing to {provider} is a Pro feature.")

    # 3. Get Handler
    from app.services.integrations import get_integration_handler
    
    handler = get_integration_handler(provider)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported.")

    try:
        await handler.sync(integration, note)
    except Exception as e:
        print(f"Share Error ({provider}): {e}")
        raise HTTPException(status_code=500, detail=f"Sharing failed: {str(e)}")

    return {"status": "success", "provider": provider}

from app.schemas import NoteEditRequest

@router.post("/{note_id}/edit", response_model=NoteResponse)
async def edit_note(
    note_id: str,
    req: NoteEditRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually edit note content (title, summary, action items).
    Updates semantic embedding automatically.
    """
    result = await db.execute(select(Note).where(Note.id == note_id, Note.user_id == current_user.id))
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    note.title = req.title
    note.summary = req.summary
    note.action_items = req.action_items
    
    # Update Embedding for semantic search continuity
    search_content = f"{note.title} {note.summary} {note.transcription_text or ''}"
    try:
        from app.services.ai_service import ai_service
        note.embedding = await ai_service.generate_embedding(search_content)
    except Exception as e:
        import logging
        logging.error(f"Failed to update embedding during edit: {e}")

    await db.commit()
    await db.refresh(note)
    return note
