import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add the app directory to the python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models.subscription import SubscriptionPlan, PlanType

async def seed_plans():
    print("Seeding subscription plans...")
    async with AsyncSessionLocal() as session:
        plans = [
            {
                "plan_type": PlanType.STARTER,
                "name": "Starter Plan",
                "description": "Essential tools for small-scale broiler farmers.",
                "monthly_price": Decimal("0.00"),
                "yearly_price": Decimal("0.00"),
                "features": [
                    "flock_tracking",
                    "basic_finance",
                    "mortality_logs",
                    "90_day_history"
                ],
                "popular": False,
            },
            {
                "plan_type": PlanType.PROFESSIONAL,
                "name": "Professional Plan",
                "description": "Advanced analytics and financial tools for growing farms.",
                "monthly_price": Decimal("500.00"),
                "yearly_price": Decimal("5000.00"),
                "features": [
                    "flock_tracking",
                    "advanced_finance",
                    "mortality_logs",
                    "full_history",
                    "export_data",
                    "inventory_management",
                    "custom_categories"
                ],
                "popular": True,
            },
            {
                "plan_type": PlanType.ENTERPRISE,
                "name": "Enterprise Plan",
                "description": "Full-suite management for large-scale commercial poultry operations.",
                "monthly_price": Decimal("2000.00"),
                "yearly_price": Decimal("20000.00"),
                "features": [
                    "all_pro_features",
                    "multi_farm_support",
                    "employee_management",
                    "api_access",
                    "priority_support",
                    "ai_advisory"
                ],
                "popular": False,
            }
        ]

        for plan_data in plans:
            # Check if plan exists
            stmt = select(SubscriptionPlan).filter(SubscriptionPlan.plan_type == plan_data["plan_type"])
            result = await session.execute(stmt)
            existing_plan = result.scalars().first()

            if existing_plan:
                print(f"Updating existing plan: {plan_data['plan_type']}")
                for key, value in plan_data.items():
                    setattr(existing_plan, key, value)
            else:
                print(f"Creating new plan: {plan_data['plan_type']}")
                new_plan = SubscriptionPlan(**plan_data)
                session.add(new_plan)
        
        await session.commit()
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_plans())
