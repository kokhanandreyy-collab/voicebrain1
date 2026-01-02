from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from infrastructure.database import get_db
from app.models import User, Plan, Integration, AdminLog, Note
from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from pydantic import BaseModel

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# --- Dependency ---
async def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# --- Schemas ---
class PlanUpdate(BaseModel):
    price_monthly_usd: Optional[float] = None
    price_yearly_usd: Optional[float] = None
    price_monthly_rub: Optional[float] = None
    price_yearly_rub: Optional[float] = None
    features: Optional[dict] = None 
    is_active: Optional[bool] = None

class AdminStats(BaseModel):
    total_users: int
    total_mrr_cents: int
    total_notes_processed: int
    active_integrations: int

class ChartDataPoint(BaseModel):
    name: str # Date or Label
    value: int

class AdminCharts(BaseModel):
    growth: List[ChartDataPoint]
    integrations: List[ChartDataPoint]

# --- Endpoints ---

@router.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    offset = (page - 1) * limit
    query = select(User)
    
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
        
    if sort_by == 'usage':
        query = query.order_by(desc(User.monthly_usage_seconds))
    else:
        query = query.order_by(desc(User.created_at))
        
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Just return raw users for now, can use Pydantic schema later
    return users

@router.get("/stats", response_model=AdminStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    # Total Users
    total_users = await db.scalar(select(func.count(User.id)))
    
    # MRR (Approximate based on plans)
    # This is a basic estimation. Real MRR should come from Stripe/Payment Provider webhooks.
    pro_users = await db.scalar(select(func.count(User.id)).where(User.tier == 'pro'))
    premium_users = await db.scalar(select(func.count(User.id)).where(User.tier == 'premium'))
    
    # Fetch Plan prices
    plans_res = await db.execute(select(Plan))
    plans = {p.id: p for p in plans_res.scalars().all()} # Use ID
    
    # Simple MRR Estimation (using RUB pricing for simplicity in report)
    pro_price = plans.get('pro').price_monthly_rub if plans.get('pro') else 490
    premium_price = plans.get('premium').price_monthly_rub if plans.get('premium') else 990
    
    mrr = (pro_users * pro_price) + (premium_users * premium_price)
          
    # Total Notes
    total_notes = await db.scalar(select(func.count(Note.id)))
    
    # Active Integrations
    active_integrations = await db.scalar(select(func.count(Integration.id)))
    
    return {
        "active_integrations": active_integrations or 0,
        "total_users": total_users,
        "total_mrr_cents": mrr,
        "total_notes_processed": total_notes
    }

@router.get("/charts", response_model=AdminCharts)
async def get_admin_charts(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    # 1. Growth (Last 7 Days)
    # Note: func.date works in Postgres/SQLite. 
    # For a more robust DB agnostic approach, we might fetch last N users and aggregate in Py, 
    # but let's try SQL grouping first.
    
    # SQLite uses strftime('%Y-%m-%d', created_at) usually, Postgres uses date(created_at) or cast.
    # We will assume ONE DB type or try a generic approach if simple.
    # Let's just fetch users from last 7 days and aggregate in code to be safe and simple.
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    res = await db.execute(select(User.created_at).where(User.created_at >= seven_days_ago))
    dates = res.scalars().all()
    
    # Aggregate
    growth_map = {}
    # init last 7 days keys
    for i in range(7):
        d = (datetime.utcnow() - timedelta(days=6-i)).strftime("%Y-%m-%d") # Today is included? Or 7 days? 
        # Let's do 0 to 6
        growth_map[d] = 0
        
    for d in dates:
        key = d.strftime("%Y-%m-%d")
        if key in growth_map:
            growth_map[key] += 1
            
    growth_data = [ChartDataPoint(name=k, value=v) for k, v in growth_map.items()]
    
    # 2. Integrations Share
    # Group by provider
    # select provider, count(*) from integrations group by provider
    int_res = await db.execute(
        select(Integration.provider, func.count(Integration.id))
        .group_by(Integration.provider)
    )
    rows = int_res.all() # list of (provider, count)
    
    integration_data = [
        ChartDataPoint(name=row[0].replace('_', ' ').capitalize(), value=row[1]) 
        for row in rows
    ]
    
    return {
        "growth": growth_data,
        "integrations": integration_data
    }

@router.get("/plans")
async def get_plans(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(Plan))
    return result.scalars().all()

@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    updates: PlanUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(Plan).where(Plan.id == plan_id))
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
        
    if updates.price_monthly_usd is not None:
        plan.price_monthly_usd = updates.price_monthly_usd
    if updates.price_yearly_usd is not None:
        plan.price_yearly_usd = updates.price_yearly_usd
    if updates.price_monthly_rub is not None:
        plan.price_monthly_rub = updates.price_monthly_rub
    if updates.price_yearly_rub is not None:
        plan.price_yearly_rub = updates.price_yearly_rub
        
    if updates.features is not None:
        plan.features = updates.features
    if updates.is_active is not None:
        plan.is_active = updates.is_active
        
    # Log Action
    log = AdminLog(
        admin_id=admin.id,
        action="UPDATE_PLAN",
        target_id=plan.id,
        details=updates.dict(exclude_unset=True)
    )
    db.add(log)
    
    await db.commit()
    await db.refresh(plan)
    return plan

@router.post("/impersonate/{user_id}")
async def impersonate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalars().first()
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Generate Token
    # Maybe add a special claim 'impersonator_id'
    access_token = create_access_token(
        data={"sub": target_user.email, "impersonator": admin.id},
        expires_delta=timedelta(minutes=60) # Short lived
    )
    
    # Log
    log = AdminLog(
        admin_id=admin.id,
        action="IMPERSONATE_USER",
        target_id=target_user.id
    )
    db.add(log)
    await db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

from app.models import PromoCode

class CreatePromoCode(BaseModel):
    code: str
    discount_percent: int
    usage_limit: int = 100

class GrantSubscription(BaseModel):
    tier: str # 'pro', 'premium' (or 'free' to revoke)
    duration_days: Optional[int] = None # None = lifetime or until cancelled manually

@router.get("/promocodes")
async def get_promocodes(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    result = await db.execute(select(PromoCode).order_by(desc(PromoCode.created_at)))
    return result.scalars().all()

@router.post("/promocodes")
async def create_promocode(
    promo: CreatePromoCode,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    # Check uniqueness
    existing = await db.execute(select(PromoCode).where(PromoCode.code == promo.code))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Code already exists")

    new_code = PromoCode(
        code=promo.code,
        discount_percent=promo.discount_percent,
        usage_limit=promo.usage_limit
    )
    db.add(new_code)
    
    log = AdminLog(admin_id=admin.id, action="CREATE_PROMO", target_id=new_code.id, details=promo.dict())
    db.add(log)
    
    await db.commit()
    return new_code

@router.delete("/promocodes/{id}")
async def delete_promocode(
    id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    res = await db.execute(select(PromoCode).where(PromoCode.id == id))
    code = res.scalars().first()
    if code:
        await db.delete(code)
        
        log = AdminLog(admin_id=admin.id, action="DELETE_PROMO", target_id=id)
        db.add(log)
        
        await db.commit()
    return {"status": "deleted"}

@router.post("/users/{user_id}/grant_subscription")
async def grant_subscription(
    user_id: str,
    grant: GrantSubscription,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.tier = grant.tier
    user.is_pro = grant.tier in ['pro', 'premium']
    
    # Reset cycle start to now
    user.billing_cycle_start = datetime.utcnow()
    
    # If duration specified, we might want to store expiry somewhere?
    # For now, simplistic implementation: just set it. 
    # Logic note: If duration_days is set, we might not have a field for "subscription_expires_at".
    # User model relies on 'billing_cycle_start' + 'billing_period'.
    # If it's a Manual Grant, it implies "Free access for X days".
    # We lack a 'subscription_expires_at' column.
    
    # Let's assume manual grants just serve as "Active until manually revoked or we implement expiry check for manual grants"
    # Or we can reuse billing logic by setting billing period roughly?
    # For MVP: Just setting the Tier is enough.
    
    log = AdminLog(admin_id=admin.id, action="GRANT_SUB", target_id=user.id, details=grant.dict())
    db.add(log)
    
    await db.commit()
    return {"status": "granted", "tier": user.tier}

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_active = False
    # Optionally logout user by revoking tokens? (Not implemented yet globally)
    
    log = AdminLog(admin_id=admin.id, action="BAN_USER", target_id=user.id)
    db.add(log)
    
    await db.commit()
    return {"status": "banned", "is_active": user.is_active}

# --- System Prompts ---

class UpdateSystemPrompt(BaseModel):
    text: str

@router.get("/prompts")
async def list_sys_prompts(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models import SystemPrompt
    result = await db.execute(select(SystemPrompt).order_by(SystemPrompt.key))
    return result.scalars().all()

@router.put("/prompts/{key}")
async def update_sys_prompt(
    key: str,
    update: UpdateSystemPrompt,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models import SystemPrompt
    from app.services.ai_service import ai_service
    
    result = await db.execute(select(SystemPrompt).where(SystemPrompt.key == key))
    prompt = result.scalars().first()
    
    if not prompt:
        # Create it if not exists (allows adding new keys dynamically)
        prompt = SystemPrompt(key=key, text=update.text)
        db.add(prompt)
    else:
        prompt.text = update.text
        prompt.version += 1
        
    log = AdminLog(admin_id=admin.id, action="UPDATE_PROMPT", target_id=key, details={"version": prompt.version})
    db.add(log)
    
    await db.commit()
    
    # Invalidate Cache
    if ai_service.redis:
        await ai_service.redis.delete(f"system_prompt:{key}")
        
    return prompt
