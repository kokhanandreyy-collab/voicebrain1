import asyncio
from app.infrastructure.database import AsyncSessionLocal, engine
from app.models import Plan, Base
from sqlalchemy import text

async def seed_plans():
    # Helper to drop/create
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS plans CASCADE"))
        # Re-create all tables is risky if we just want plans.
        # But SQLA create_all will only create missing. 
        # Since I dropped 'plans', create_all will recreate 'plans'.
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Seed
        pro = Plan(
            id="pro", 
            name="Pro",
            price_monthly_usd=9.99,
            price_yearly_usd=96.00,
            price_monthly_rub=490.00,
            price_yearly_rub=3990.00,
            features={"monthly_transcription_seconds": 72000, "storage_months": 12, "allowed_integrations": ["notion", "google_calendar"]},
            is_active=True
        )
        session.add(pro)

        premium = Plan(
            id="premium",
            name="Premium",
            price_monthly_usd=19.00,
            price_yearly_usd=190.00,
            price_monthly_rub=990.00,
            price_yearly_rub=7990.00,
            features={"monthly_transcription_seconds": -1, "storage_months": -1, "allowed_integrations": ["notion", "google_calendar", "zapier", "bitrix24"]},
            is_active=True
        )
        session.add(premium)
        
        await session.commit()
        print("Plans table recreated and seeded.")

if __name__ == "__main__":
    asyncio.run(seed_plans())
