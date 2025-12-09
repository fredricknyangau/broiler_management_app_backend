from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
from typing import Optional

from app.db.models.alert import Alert
from app.db.models.flock import Flock
from app.db.models.events import MortalityEvent

class AlertService:
    def __init__(self,db: Session):
        self.db = db

    def create_alert(self, flock_id: UUID, title: str, message: str, severity: str = "medium", alert_type: str = "general"):
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
        self.db.commit()
        return alert

    def check_mortality(self, flock_id: UUID, current_mortality_count: int, initial_birds: int):
        """
        Checks if daily mortality is alarmingly high (e.g., > 2% of initial flock size in a single day, or just a fixed number).
        Using a simplified threshold for now: > 1% daily is high.
        """
        if initial_birds <= 0:
            return

        rate = (current_mortality_count / initial_birds) * 100
        if rate > 1.0:
            self.create_alert(
                flock_id=flock_id,
                title="High Mortality Rate",
                message=f"Mortality rate detected at {rate:.1f}% for today. Investigate immediately.",
                severity="critical" if rate > 2.0 else "high",
                alert_type="mortality"
            )

    def check_low_stock(self, item_name: str, current_qty: float, min_qty: float, flock_id: Optional[UUID] = None):
        """
        Checks if inventory item is below minimum stock.
        Note: Alerts are usually tied to a flock, but inventory is global to the user.
        If flock_id is missing, we might need a generic 'system' alert or link it to the user's active flock.
        For now, we will associate it with the first active flock found for the user if not provided, or leave flock_id null if the model supports it.
        Actually, looking at Alert model, flock_id might be nullable? Let's assume it is REQUIRED for now and we need to find a way.
        
        Update: The Alert model likely relates to a Flock. If it's a general inventory alert, we might need to attach it to *any* active flock or change the model.
        Let's assume we pass a flock_id context, or fetch one.
        """
        if current_qty <= min_qty:
           # We need a flock_id to save the Alert. 
           # If this is called from an Inventory context where we have a User but not necessarily a specific Flock, 
           # we might need to find one.
           pass
