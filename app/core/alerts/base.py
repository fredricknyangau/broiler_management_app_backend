from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertResult:
    """Result of alert rule evaluation"""
    should_alert: bool
    severity: AlertSeverity
    title: str
    message: str
    metadata: Optional[Dict[str, Any]] = None


class AlertRule(ABC):
    """Base class for all alert rules"""
    
    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Unique identifier for this rule"""
        pass
    
    @property
    @abstractmethod
    def alert_type(self) -> str:
        """Type/category of alert"""
        pass
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        """
        Evaluate the rule against provided context.
        Returns AlertResult if alert should be triggered, None otherwise.
        """
        pass
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.rule_name}')>"