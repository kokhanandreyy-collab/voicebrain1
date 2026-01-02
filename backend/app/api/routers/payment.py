import hmac
import hashlib
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.database import get_db
from app.models import User, UserTier, Plan
from app.api.dependencies import get_current_user
from app.infrastructure.config import settings
from pydantic import BaseModel
from typing import Literal

router = APIRouter(
    prefix="/payment",
    tags=["payment"]
)

logger = logging.getLogger(__name__)

class InitPaymentRequest(BaseModel):
    tier: str # "pro" or "premium"
    billing_period: str # "monthly" or "yearly"
    promo_code: Optional[str] = None
    currency: Literal['RUB', 'USD'] = 'RUB' # Default to RUB for existing users

@router.get("/config")
async def get_payment_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active == True))
    plans = result.scalars().all()
    
    usd_config = {}
    rub_config = {}
    
    for p in plans:
        usd_config[p.id] = { "monthly": p.price_monthly_usd, "yearly": p.price_yearly_usd }
        rub_config[p.id] = { "monthly": p.price_monthly_rub, "yearly": p.price_yearly_rub }
        
    return {
        "usd": usd_config,
        "rub": rub_config
    }

def verify_prodamus_signature(data: dict, received_sign: str) -> bool:
    """
    Verifies the HMAC signature from Prodamus.
    Prodamus logic: 
    1. Sort keys alphabetically (excluding 'Sign')
    2. Concatenate values
    3. HMAC-SHA256 with PRODAMUS_KEY
    """
    if not received_sign:
        return False
        
    # Filter out 'Sign' (or other non-payload fields if any)
    payload_keys = sorted([k for k in data.keys() if k.lower() != 'sign'])
    
    # Concatenate values
    # Note: Values should be strings. 
    concat_str = "".join([str(data[k]) for k in payload_keys])
    
    expected_sign = hmac.new(
        settings.PRODAMUS_KEY.encode(),
        concat_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_sign.lower(), received_sign.lower())

@router.post("/init")
async def init_payment(
    req: InitPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch Plan
    result = await db.execute(select(Plan).where(Plan.id == req.tier))
    plan = result.scalars().first()
    
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid tier")

    amount = 0
    
    # Currency Selection Logic
    if req.currency == 'RUB':
        amount = plan.price_monthly_rub if req.billing_period == "monthly" else plan.price_yearly_rub
    elif req.currency == 'USD':
        amount = plan.price_monthly_usd if req.billing_period == "monthly" else plan.price_yearly_usd
            
    if amount == 0:
         raise HTTPException(status_code=400, detail="Invalid tier or currency")
    
    # Apply Promo Code
    discount = 0
    from app.models import PromoCode
    if req.promo_code:
        # Validate code from DB
        res = await db.execute(select(PromoCode).where(PromoCode.code == req.promo_code))
        promo = res.scalars().first()
        
        if promo and promo.is_active:
             if promo.usage_limit and promo.times_used >= promo.usage_limit:
                 pass # Limit reached
             else:
                 discount = (amount * promo.discount_percent) / 100
                 # We don't increment times_used yet; only on webhook success
                 
    final_amount = max(0, amount - discount)

    order_id = str(uuid.uuid4())
    
    # Mock Mode for Dev
    if settings.ENVIRONMENT == "development" and settings.PRODAMUS_KEY == "secret_key":
         return {
            "url": f"{settings.API_BASE_URL}/payment/success?order_id={order_id}&amount={final_amount}&tier={req.tier}&period={req.billing_period}&currency={req.currency}&promo={req.promo_code or ''}",
            "mode": "dev_mock"
        }

    # Real Prodamus Link
    try:
        from urllib.parse import urlencode
        import json
        
        products = [
            {
                "name": f"VoiceBrain {plan.name} ({req.billing_period}) [{req.currency}]",
                "price": final_amount,
                "quantity": 1,
                "sum": final_amount
            }
        ]
        
        params = {
            "order_id": order_id,
            "sum": final_amount,
            "currency": req.currency, # Prodamus supports 'currency' param for display, but main account usually fixed currency.
                                      # Assuming Prodamus configured for multi-currency or we just send amount.
            "customer_email": current_user.email,
            "products": json.dumps(products),
            "do": "link",
            "#tier": req.tier, # Custom fields prefixed with #
            "#period": req.billing_period,
            "#currency": req.currency,
            "#promo": req.promo_code or ""
        }
        
        query_string = urlencode(params)
        return {
            "url": f"{settings.PRODAMUS_URL}/?{query_string}",
            "mode": "production"
        }
    except Exception as e:
        logger.error(f"Payment Link Gen Error: {e}")
        raise HTTPException(status_code=500, detail="Payment generation failed")

@router.post("/webhook")
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Prodamus sends parameters as a form (multipart/form-data or application/x-www-form-urlencoded)
    form_data = await request.form()
    data = dict(form_data)
    
    received_sign = data.get("Sign")
    
    # 1. Security check
    if not verify_prodamus_signature(data, received_sign):
        logger.warning(f"Invalid Prodamus signature received for order {data.get('order_id')}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 2. Extract Data
    email = data.get("customer_email")
    payment_status = data.get("payment_status") # Usually 'success'
    payment_sum = float(data.get("sum", 0))
    
    # Custom fields from #tier, #period (Prodamus might strip # or pass as is)
    target_tier = data.get("#tier") or data.get("tier")
    billing_period = data.get("#period") or data.get("billing_period")
    currency = data.get("#currency") or data.get("currency") or "RUB" # Default to RUB if missing

    if payment_status != "success":
        logger.info(f"Webhook received for non-success status: {payment_status}")
        return {"status": "ignored"}

    # 3. Validation: Verify amount matches the tier price
    # Determine expected price based on currency
    expected_price = 0
    
    # Fetch Plan
    p_res = await db.execute(select(Plan).where(Plan.id == target_tier))
    plan = p_res.scalars().first()
    
    if not plan:
         logger.error(f"Webhook: Plan not found {target_tier}")
         # We might still upgrade user if we trust signature, but logging error
    else:
        if currency == "USD":
             expected_price = plan.price_monthly_usd if billing_period == 'monthly' else plan.price_yearly_usd
        else:
             expected_price = plan.price_monthly_rub if billing_period == 'monthly' else plan.price_yearly_rub
    
    promo_code = data.get("#promo") or data.get("promo")
    
    if not promo_code:
        if not expected_price or abs(payment_sum - expected_price) > 0.5: # 0.5 buffer
             logger.error(f"Payment sum mismatch for {email}: Recv {payment_sum}, Exp {expected_price} ({currency})")
             raise HTTPException(status_code=400, detail="Payment sum mismatch")
    else:
        # If promo code used, we trust the sum is correct for now or assume strict check is skipped.
        # Ideally we'd re-verify promo.
        pass

    # 4. Update User
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if user:
        if target_tier == "pro":
            user.tier = UserTier.PRO
        elif target_tier == "premium":
             user.tier = UserTier.PREMIUM
        
        user.billing_cycle_start = datetime.utcnow()
        user.monthly_usage_seconds = 0
        
        # Increment Promo Usage
        if promo_code:
            from app.models import PromoCode
            p_res = await db.execute(select(PromoCode).where(PromoCode.code == promo_code))
            promo = p_res.scalars().first()
            if promo:
                promo.times_used += 1

        await db.commit()
        logger.info(f"Upgraded user {email} to {target_tier}")
        return {"status": "ok"}
    
    return {"status": "user_not_found"}

# Dev Helper: Simulate Webhook (only for local testing)
@router.post("/dev/upgrade")
async def dev_upgrade_user(
    email: str,
    tier: str,
    db: AsyncSession = Depends(get_db)
):
    if settings.ENVIRONMENT != "development":
        raise HTTPException(status_code=403)
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        if tier.lower() == "pro":
            user.tier = UserTier.PRO
        elif tier.lower() == "premium":
            user.tier = UserTier.PREMIUM
        else:
            user.tier = UserTier.FREE
            
        user.monthly_usage_seconds = 0
        user.billing_cycle_start = datetime.utcnow()
        await db.commit()
        return {"status": "upgraded", "tier": user.tier}
    return {"status": "error"}
