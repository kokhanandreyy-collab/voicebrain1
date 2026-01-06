from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Dict, Any

from infrastructure.database import get_db
from app.models import User
from app.api.dependencies import get_current_user

router = APIRouter(
    tags=["Settings"]
)

class FeatureFlagsUpdate(BaseModel):
    flags: Dict[str, Any]

@router.put("/feature-flags", summary="Update Feature Flags", description="Modify user-specific feature flags for A/B testing or experimental feature access.")
async def update_feature_flags(
    updates: FeatureFlagsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user feature flags."""
    # Merge updates
    current_flags = current_user.feature_flags or {}
    updated_flags = {**current_flags, **updates.flags}
    
    current_user.feature_flags = updated_flags
    await db.commit()
    await db.refresh(current_user)
    
    return {"status": "success", "feature_flags": current_user.feature_flags}

@router.get("/feature-flags", summary="Get Feature Flags", description="Retrieve current feature flags enabled for the authenticated user.")
async def get_feature_flags(
    current_user: User = Depends(get_current_user)
):
    return {"feature_flags": current_user.feature_flags or {}}
