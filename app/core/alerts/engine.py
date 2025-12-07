from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.core.alerts.rules import (
    LowTemperatureAlert,
    HighTemperatureAlert,
    HighMortalityAlert,
    LowFeedAlert,
    LowWaterAlert,
    StressedChicksAlert,
    VaccinationDueAlert,
    PoorGrowthAlert
)
from app.core.alerts.base import AlertRule, AlertResult
from app.db.models.alert import Alert
from uuid import UUID
from datetime import datetime, timedelta


class AlertEngine:
    """Evaluates alert rules and manages alert lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
        self.rules: List[AlertRule] = [
            LowTemperatureAlert(),
            HighTemperatureAlert(),
            HighMortalityAlert(),
            LowFeedAlert(),
            LowWaterAlert(),
            StressedChicksAlert(),
            VaccinationDueAlert(),
            PoorGrowthAlert()
        ]
    
    def evaluate_all(self, flock_id: UUID, context: Dict[str, Any]) -> List[Alert]:
        """
        Evaluate all rules against provided context.
        Returns list of alerts that were triggered.
        """
        triggered_alerts = []
        
        for rule in self.rules:
            result = rule.evaluate(context)
            if result and result.should_alert:
                # Check for existing active alert of same type
                existing = self._get_active_alert(flock_id, rule.alert_type)
                
                if existing:
                    # Update existing alert if severity changed
                    if existing.severity != result.severity.value:
                        existing.severity = result.severity.value
                        existing.message = result.message
                        existing.metadata = result.metadata
                        existing.triggered_at = datetime.utcnow()
                        self.db.commit()
                        triggered_alerts.append(existing)
                else:
                    # Create new alert
                    alert = self._create_alert(flock_id, rule.alert_type, result)
                    triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def _get_active_alert(self, flock_id: UUID, alert_type: str) -> Alert:
        """Get active alert of specific type for a flock"""
        return self.db.query(Alert).filter(
            Alert.flock_id == flock_id,
            Alert.alert_type == alert_type,
            Alert.status == "active"
        ).first()
    
    def _create_alert(
        self, 
        flock_id: UUID, 
        alert_type: str, 
        result: AlertResult
    ) -> Alert:
        """Create a new alert"""
        alert = Alert(
            flock_id=flock_id,
            alert_type=alert_type,
            severity=result.severity.value,
            title=result.title,
            message=result.message,
            metadata=result.metadata,
            status="active"
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def acknowledge_alert(self, alert_id: UUID) -> bool:
        """Mark alert as acknowledged"""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False
        
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def resolve_alert(self, alert_id: UUID) -> bool:
        """Mark alert as resolved"""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False
        
        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def auto_resolve_stale_alerts(self, hours: int = 24):
        """Auto-resolve alerts that haven't been updated in N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        stale_alerts = self.db.query(Alert).filter(
            Alert.status == "active",
            Alert.triggered_at < cutoff
        ).all()
        
        for alert in stale_alerts:
            alert.status = "resolved"
            alert.resolved_at = datetime.utcnow()
        
        self.db.commit()
        return len(stale_alerts)