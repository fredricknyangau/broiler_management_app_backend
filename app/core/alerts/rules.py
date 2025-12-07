from datetime import date, timedelta
from typing import Dict, Any, Optional
from app.core.alerts.base import AlertRule, AlertResult, AlertSeverity


class LowTemperatureAlert(AlertRule):
    """Alert when brooding temperature is too low"""
    
    MIN_TEMP_WEEK_1 = 32.0
    MIN_TEMP_WEEK_2 = 29.3
    MIN_TEMP_WEEK_3 = 26.6
    MIN_TEMP_WEEK_4_PLUS = 24.0
    
    @property
    def rule_name(self) -> str:
        return "low_temperature"
    
    @property
    def alert_type(self) -> str:
        return "temperature"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        temperature = context.get("temperature_celsius")
        days_old = context.get("days_old", 0)
        
        if temperature is None:
            return None
        
        # Determine minimum temperature based on age
        if days_old <= 7:
            min_temp = self.MIN_TEMP_WEEK_1
            week = "week 1"
        elif days_old <= 14:
            min_temp = self.MIN_TEMP_WEEK_2
            week = "week 2"
        elif days_old <= 21:
            min_temp = self.MIN_TEMP_WEEK_3
            week = "week 3"
        else:
            min_temp = self.MIN_TEMP_WEEK_4_PLUS
            week = "week 4+"
        
        if temperature < min_temp:
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="Temperature Too Low",
                message=f"Temperature is {temperature}°C, below minimum of {min_temp}°C for {week}. "
                       f"Chicks may be cold-stressed. Check heat source immediately.",
                metadata={
                    "current_temp": float(temperature),
                    "minimum_temp": min_temp,
                    "days_old": days_old
                }
            )
        
        return None


class HighTemperatureAlert(AlertRule):
    """Alert when brooding temperature is too high"""
    
    MAX_TEMP = 38.0
    
    @property
    def rule_name(self) -> str:
        return "high_temperature"
    
    @property
    def alert_type(self) -> str:
        return "temperature"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        temperature = context.get("temperature_celsius")
        
        if temperature is None:
            return None
        
        if temperature > self.MAX_TEMP:
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="Temperature Too High",
                message=f"Temperature is {temperature}°C, above maximum of {self.MAX_TEMP}°C. "
                       f"Chicks may be heat-stressed. Reduce heat source and improve ventilation.",
                metadata={"current_temp": float(temperature), "maximum_temp": self.MAX_TEMP}
            )
        
        return None


class HighMortalityAlert(AlertRule):
    """Alert when mortality rate exceeds acceptable threshold"""
    
    MAX_MORTALITY_RATE_WEEK_1 = 1.0  # 1% in first week
    MAX_MORTALITY_RATE_OVERALL = 5.0  # 5% overall
    
    @property
    def rule_name(self) -> str:
        return "high_mortality"
    
    @property
    def alert_type(self) -> str:
        return "mortality"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        mortality_rate = context.get("mortality_rate_percent")
        days_old = context.get("days_old", 0)
        total_deaths = context.get("total_deaths", 0)
        
        if mortality_rate is None:
            return None
        
        # Check week 1 threshold
        if days_old <= 7 and mortality_rate > self.MAX_MORTALITY_RATE_WEEK_1:
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="High Mortality in Week 1",
                message=f"Mortality rate is {mortality_rate}%, exceeding {self.MAX_MORTALITY_RATE_WEEK_1}% threshold "
                       f"for first week ({total_deaths} birds). Immediate investigation required.",
                metadata={
                    "mortality_rate": mortality_rate,
                    "threshold": self.MAX_MORTALITY_RATE_WEEK_1,
                    "total_deaths": total_deaths,
                    "days_old": days_old
                }
            )
        
        # Check overall threshold
        if mortality_rate > self.MAX_MORTALITY_RATE_OVERALL:
            severity = AlertSeverity.CRITICAL if mortality_rate > 8.0 else AlertSeverity.WARNING
            return AlertResult(
                should_alert=True,
                severity=severity,
                title="High Overall Mortality",
                message=f"Mortality rate is {mortality_rate}%, exceeding {self.MAX_MORTALITY_RATE_OVERALL}% threshold "
                       f"({total_deaths} birds). Review health management practices.",
                metadata={
                    "mortality_rate": mortality_rate,
                    "threshold": self.MAX_MORTALITY_RATE_OVERALL,
                    "total_deaths": total_deaths
                }
            )
        
        return None


class LowFeedAlert(AlertRule):
    """Alert when feed level is low or empty"""
    
    @property
    def rule_name(self) -> str:
        return "low_feed"
    
    @property
    def alert_type(self) -> str:
        return "feed"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        feed_level = context.get("feed_level")
        
        if feed_level == "empty":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="Feed Supply Empty",
                message="Feed supply is empty. Chicks must have continuous access to feed. Refill immediately.",
                metadata={"feed_level": feed_level}
            )
        
        if feed_level == "low":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.WARNING,
                title="Feed Supply Low",
                message="Feed supply is running low. Restock soon to prevent interruption.",
                metadata={"feed_level": feed_level}
            )
        
        return None


class LowWaterAlert(AlertRule):
    """Alert when water level is low or empty"""
    
    @property
    def rule_name(self) -> str:
        return "low_water"
    
    @property
    def alert_type(self) -> str:
        return "water"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        water_level = context.get("water_level")
        
        if water_level == "empty":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="Water Supply Empty",
                message="Water supply is empty. Chicks require constant access to clean water. Refill immediately.",
                metadata={"water_level": water_level}
            )
        
        if water_level == "low":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.WARNING,
                title="Water Supply Low",
                message="Water supply is running low. Refill to maintain adequate hydration.",
                metadata={"water_level": water_level}
            )
        
        return None


class StressedChicksAlert(AlertRule):
    """Alert when chick behavior indicates stress"""
    
    @property
    def rule_name(self) -> str:
        return "stressed_chicks"
    
    @property
    def alert_type(self) -> str:
        return "behavior"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        behavior = context.get("chick_behavior")
        temperature = context.get("temperature_celsius")
        
        if behavior == "huddling":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.WARNING,
                title="Chicks Huddling Together",
                message=f"Chicks are huddling, indicating they may be too cold. "
                       f"Current temperature: {temperature}°C. Increase heat source.",
                metadata={"behavior": behavior, "temperature": temperature}
            )
        
        if behavior == "panting":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.WARNING,
                title="Chicks Panting",
                message=f"Chicks are panting, indicating they may be too hot. "
                       f"Current temperature: {temperature}°C. Reduce heat and improve ventilation.",
                metadata={"behavior": behavior, "temperature": temperature}
            )
        
        if behavior == "lethargic":
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="Lethargic Chicks",
                message="Chicks appear lethargic. This may indicate illness, poor nutrition, or environmental stress. "
                       "Inspect flock immediately and consult veterinarian if needed.",
                metadata={"behavior": behavior}
            )
        
        return None


class VaccinationDueAlert(AlertRule):
    """Alert when vaccination is due or overdue"""
    
    @property
    def rule_name(self) -> str:
        return "vaccination_due"
    
    @property
    def alert_type(self) -> str:
        return "vaccination"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        next_due_date = context.get("next_vaccination_due_date")
        vaccine_name = context.get("vaccine_name", "Unknown vaccine")
        
        if not next_due_date:
            return None
        
        today = date.today()
        days_until = (next_due_date - today).days
        
        # Overdue
        if days_until < 0:
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.CRITICAL,
                title="Vaccination Overdue",
                message=f"{vaccine_name} vaccination was due on {next_due_date}. "
                       f"Administer as soon as possible to maintain protection.",
                metadata={
                    "vaccine_name": vaccine_name,
                    "due_date": str(next_due_date),
                    "days_overdue": abs(days_until)
                }
            )
        
        # Due today
        if days_until == 0:
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.WARNING,
                title="Vaccination Due Today",
                message=f"{vaccine_name} vaccination is due today.",
                metadata={
                    "vaccine_name": vaccine_name,
                    "due_date": str(next_due_date)
                }
            )
        
        # Due within 2 days
        if days_until <= 2:
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.INFO,
                title="Upcoming Vaccination",
                message=f"{vaccine_name} vaccination is due in {days_until} day(s) on {next_due_date}.",
                metadata={
                    "vaccine_name": vaccine_name,
                    "due_date": str(next_due_date),
                    "days_until": days_until
                }
            )
        
        return None


class PoorGrowthAlert(AlertRule):
    """Alert when weight gain is below expected"""
    
    # Expected: chicks should multiply weight 4.5x by day 7
    EXPECTED_WEIGHT_DAY_7 = 180  # grams (assuming 40g day-old chick)
    
    @property
    def rule_name(self) -> str:
        return "poor_growth"
    
    @property
    def alert_type(self) -> str:
        return "growth"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[AlertResult]:
        days_old = context.get("days_old")
        average_weight = context.get("average_weight_grams")
        
        if not days_old or not average_weight:
            return None
        
        # Check day 7 weight
        if days_old == 7 and average_weight < self.EXPECTED_WEIGHT_DAY_7:
            deficit = self.EXPECTED_WEIGHT_DAY_7 - average_weight
            return AlertResult(
                should_alert=True,
                severity=AlertSeverity.WARNING,
                title="Below Expected Weight at Day 7",
                message=f"Average weight is {average_weight}g, below expected {self.EXPECTED_WEIGHT_DAY_7}g "
                       f"(deficit: {deficit}g). Review feed quality, quantity, and health management.",
                metadata={
                    "actual_weight": float(average_weight),
                    "expected_weight": self.EXPECTED_WEIGHT_DAY_7,
                    "deficit": float(deficit),
                    "days_old": days_old
                }
            )
        
        return None