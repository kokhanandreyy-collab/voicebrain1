from app.core.limiter import limiter
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserResponse, UserUpdate
from app.dependencies import get_current_user
from pydantic import EmailStr, BaseModel
from app.core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta
import uuid

router = APIRouter()

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/signup")
@limiter.limit("5/5 minute")
async def signup(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate Verification Token
    verification_token = str(uuid.uuid4())
    
    new_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        is_verified=False, # Require verification
        verification_token=verification_token
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Real Email Sending
    from app.services.email import send_email
    
    # Note: Link might need update to point to frontend, which will call API or handle routing
    # Assuming frontend is on localhost:5173
    verify_link = f"http://localhost:5173/verify?token={verification_token}"
    email_body = f"""
    <h1>Welcome to VoiceBrain!</h1>
    <p>Please verify your email address by clicking the link below:</p>
    <a href="{verify_link}">Verify Email</a>
    <p>If you didn't request this, please ignore this email.</p>
    """
    await send_email(user.email, "Verify your VoiceBrain account", email_body)
    
    return {"message": "Registration successful. Please check your email to verify your account."}

@router.get("/verify")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if user.is_verified:
        return {"message": "Email already verified"}
        
    user.is_verified = True
    user.verification_token = None
    await db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        # Don't reveal if user exists
        return {"message": "If this email is registered, you will receive a password reset link."}
    
    token = str(uuid.uuid4())
    user.reset_token = token
    await db.commit()
    
    # Real Email Sending
    from app.services.email import send_email
    
    reset_link = f"http://localhost:5173/reset-password?token={token}"
    email_body = f"""
    <h1>Reset Your Password</h1>
    <p>Click the link below to reset your password:</p>
    <a href="{reset_link}">Reset Password</a>
    <p>If you didn't request this, please ignore this email.</p>
    """
    await send_email(request.email, "Reset Your Password", email_body)
    
    return {"message": "If this email is registered, you will receive a password reset link."}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.reset_token == request.token))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    user.hashed_password = get_password_hash(request.new_password)
    user.reset_token = None
    await db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/login", response_model=Token)
@limiter.limit("5/5 minute")
async def login(request: Request, user: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalars().first()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.role is not None:
        current_user.role = user_update.role
    if user_update.has_onboarded is not None:
        current_user.has_onboarded = user_update.has_onboarded
    if user_update.language is not None:
        current_user.language = user_update.language
        
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.delete("/me", status_code=204)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently delete user account and all associated data.
    """
    from app.models import Note
    from app.core.storage import storage_client
    import os
    from urllib.parse import urlparse
    import logging

    logger = logging.getLogger(__name__)
    
    # 1. Fetch all notes to delete S3 files
    result = await db.execute(select(Note).where(Note.user_id == current_user.id))
    notes = result.scalars().all()
    
    for note in notes:
        try:
            # Delete S3 file
            key = note.storage_key
            if not key and note.audio_url and "amazonaws.com" in note.audio_url:
                try:
                    key = os.path.basename(urlparse(note.audio_url).path)
                except: pass
            
            if key:
                await storage_client.delete_file(key)
        except Exception as e:
            logger.error(f"Failed to delete S3 file for note {note.id}: {e}")
            # Continue deletion anyway
            
    # 2. Delete User (Cascade should handle notes/integrations/logs if set up, 
    # but explicit deletion is safer if relationships aren't perfect)
    
    # Explicitly delete notes first
    for note in notes:
        await db.delete(note)
        
    await db.delete(current_user)
    await db.commit()
    
    return
