from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from typing import Optional
from fastapi import BackgroundTasks
from app.services.email_service import EmailService

from app.db.models.alert import Alert
from app.db.models.flock import Flock
from app.db.models.events import MortalityEvent

class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(self, flock_id: UUID, title: str, message: str, severity: str = "medium", alert_type: str = "general"):
        """
        Creates a new alert record.
        """
        alert = Alert(
            flock_id=flock_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            status="active",
            triggered_at=datetime.utcnow()
        )
        self.db.add(alert)
        await self.db.commit()
        return alert

    async def check_mortality(self, flock_id: UUID, current_mortality_count: int, initial_birds: int):
        """
        Checks if daily mortality is alarmingly high (e.g., > 2% of initial flock size in a single day, or just a fixed number).
        Using a simplified threshold for now: > 1% daily is high.
        """
        if initial_birds <= 0:
            return

        rate = (current_mortality_count / initial_birds) * 100
        if rate > 1.0:
            await self.create_alert(
                flock_id=flock_id,
                title="High Mortality Rate",
                message=f"Mortality rate detected at {rate:.1f}% for today. Investigate immediately.",
                severity="critical" if rate > 2.0 else "high",
                alert_type="mortality"
            )

    async def check_low_stock(self, item_name: str, current_qty: float, min_qty: float, background_tasks: BackgroundTasks, flock_id: Optional[UUID] = None):
        """
        Checks if inventory item is below minimum stock.
        """
        if current_qty <= min_qty:
            # Create Alert
            await self.create_alert(
                flock_id=flock_id, # Can be None
                title=f"Low Stock: {item_name}",
                message=f"Inventory item '{item_name}' is low. Current: {current_qty}, Minimum: {min_qty}. Please restock.",
                severity="medium" if current_qty > 0 else "high",
                alert_type="low_stock"
            )
            
            # Send Email via Background Task
            subject = f"Alert: Low Stock for {item_name}"
            content = f"<h3>Low Stock Warning</h3><p>Item <b>{item_name}</b> is running low.</p><p>Current Quantity: {current_qty}</p><p>Please purchase more.</p>"
            recipients = ["farmer@example.com"] # Placeholder

            background_tasks.add_task(EmailService.send_email, recipients, subject, content)
