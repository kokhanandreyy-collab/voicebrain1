from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.future import select
from infrastructure.database import get_db
from app.models import User
from app.api.dependencies import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

router = APIRouter(
    tags=["Notifications"]
)

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

@router.post("/subscribe", summary="Web Push Subscribe", description="Register a browser push notification subscription for the current user.")
async def subscribe(
    subscription: PushSubscription,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save Web Push subscription for the user.
    """
    # Simply append to list if not exists
    subs = current_user.push_subscriptions or []
    
    # Check if exists (by endpoint)
    sub_data = subscription.model_dump()
    
    # Filter out if already exists to avoid duplicates
    # Use endpoint as unique identifier
    exists = any(s.get("endpoint") == sub_data["endpoint"] for s in subs)
    
    if not exists:
        # SQLAlchemy JSON mutation: Create new list
        new_subs = list(subs)
        new_subs.append(sub_data)
        current_user.push_subscriptions = new_subs
        
        db.add(current_user)
        await db.commit()
    
    return {"status": "subscribed"}
