from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, case
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models import User, Note, IntegrationLog, Plan, UserTier
from app.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

class UserStats(BaseModel):
    total_notes: int
    saved_time_minutes: int
    usage_minutes_this_month: int
    limit_minutes: float # Can be infinite
    balance_days_remaining: int
    subscription_renews_at: Optional[datetime]
    plan_name: str
    productivity_trend: List[Dict] # [{date: '2023-10-01', count: 5}]
    integration_usage: List[Dict] # [{name: 'notion', value: 10}]

@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Basic Counts
    total_notes = await db.scalar(
        select(func.count(Note.id)).where(Note.user_id == current_user.id)
    ) or 0
    
    total_duration = await db.scalar(
        select(func.sum(Note.duration_seconds)).where(Note.user_id == current_user.id)
    ) or 0
    
    # 2. Saved Time (Assumption: Dictation is 3x faster than typing)
    # duration is in seconds.
    saved_time_minutes = int((total_duration * 3) / 60)
    
    # 3. Usage & Limits
    usage_minutes = int(current_user.monthly_usage_seconds / 60)
    
    # Fetch Plan details
    # Fallback to constants if no plan object (for legacy/migration safety)
    limit_minutes = 120 # Default Free
    plan_name = current_user.tier
    
    # Try to fetch dynamic plan
    plan_res = await db.execute(select(Plan).where(Plan.name == current_user.tier))
    plan_obj = plan_res.scalars().first()
    
    if plan_obj:
        limit_seconds = plan_obj.features.get('monthly_transcription_seconds', 0)
        limit_minutes = limit_seconds / 60 if limit_seconds != float('inf') else float('inf')
    else:
        # Fallback to hardcoded
        if current_user.tier == 'pro': limit_minutes = 1200
        elif current_user.tier == 'premium': limit_minutes = float('inf')
        
    # 4. Balance / Renewal
    now = datetime.utcnow()
    # Assume billing_cycle_start is set. If not, default to created_at or now.
    cycle_start = current_user.billing_cycle_start or current_user.created_at or now
    
    # Calculate renewal (assuming monthly for now)
    # If yearly, we'd check billing_period
    is_yearly = current_user.billing_period == 'yearly'
    if is_yearly:
        renews_at = cycle_start + timedelta(days=365)
    else:
        renews_at = cycle_start + timedelta(days=30)
        
    # Adjust renewable if it's in the past (basic logic)
    while renews_at < now:
        renews_at += timedelta(days=365 if is_yearly else 30)
        
    days_remaining = (renews_at - now).days
    
    # 5. Productivity Trend (Last 30 Days)
    thirty_days_ago = now - timedelta(days=30)
    
    # Group by date
    # SQLite/Postgres formatting differs. Using generic day truncation if possible or just processing in python for simplicity if volume is low.
    # For now, let's just fetch recent notes and aggregate in Python to avoid DB dialect issues.
    recent_notes = await db.execute(
        select(Note.created_at)
        .where(Note.user_id == current_user.id)
        .where(Note.created_at >= thirty_days_ago)
    )
    dates = [n.date() for n in recent_notes.scalars().all()]
    
    trend_map = {}
    for i in range(30):
        d = (thirty_days_ago + timedelta(days=i)).date()
        trend_map[d.isoformat()] = 0
        
    for d in dates:
        k = d.isoformat()
        if k in trend_map:
            trend_map[k] += 1
            
    productivity_trend = [{"date": k, "count": v} for k, v in trend_map.items()]
    
    # 6. Integrations Usage
    # Count logs by integration provider (join Integration table)
    # Or just count distinct integration_ids from logs if we want simple checks
    # Better: Join IntegrationLog -> Integration -> Provider
    # But IntegrationLog might NOT link to Integration if integration deleted? 
    # Let's count successfully synced notes per provider.
    
    # For simplicity, let's query IntegrationLogs for this user
    # We need to join Integration to get the provider name
    # IntegrationLog -> Integration -> User
    
    # Correct query:
    # SELECT i.provider, COUNT(il.id) 
    # FROM integration_logs il
    # JOIN integrations i ON il.integration_id = i.id
    # WHERE i.user_id = :uid AND il.status = 'SUCCESS'
    # GROUP BY i.provider
    
    # Note: I need to import Integration model.
    from app.models import Integration
    
    logs_res = await db.execute(
        select(Integration.provider, func.count(IntegrationLog.id))
        .join(IntegrationLog, Integration.id == IntegrationLog.integration_id)
        .where(Integration.user_id == current_user.id)
        .where(IntegrationLog.status == 'SUCCESS')
        .where(IntegrationLog.created_at >= thirty_days_ago) # Recent activity filter
        .group_by(Integration.provider)
    )
    
    usage_data = [{"name": r[0], "value": r[1]} for r in logs_res.all()]
    
    # If no usage, maybe show 0 for installed ones?
    # Let's just return what we have.
    
    return UserStats(
        total_notes=total_notes,
        saved_time_minutes=saved_time_minutes,
        usage_minutes_this_month=usage_minutes,
        limit_minutes=limit_minutes,
        balance_days_remaining=days_remaining,
        subscription_renews_at=renews_at,
        plan_name=plan_name,
        productivity_trend=productivity_trend,
        integration_usage=usage_data
    )

class UpdateProfileRequest(BaseModel):
    bio: Optional[str] = None
    target_language: Optional[str] = None

@router.put("/me")
async def update_user_profile(
    req: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if req.bio is not None:
        current_user.bio = req.bio
    if req.target_language is not None:
        current_user.target_language = req.target_language
        
    await db.commit()
    await db.refresh(current_user)
    return {
        "status": "success",
        "bio": current_user.bio,
        "target_language": current_user.target_language
    }

@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "bio": current_user.bio,
        "target_language": current_user.target_language,
        "tier": current_user.tier,
        "is_active": current_user.is_active
    }
