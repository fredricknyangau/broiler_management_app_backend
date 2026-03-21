from pydantic import BaseModel, Field
from typing import Literal

class FeedRecommendationRequest(BaseModel):
    flock_age_days: int = Field(..., description="Age of the flock in days")
    current_avg_weight_kg: float = Field(..., description="Current average bird weight in kilograms")
    breed: str = Field(..., description="Breed of the broiler, e.g., Cobb 500, Ross 308")
    bird_count: int = Field(..., description="Total number of active birds in the flock")

class FeedRecommendationResponse(BaseModel):
    recommended_daily_kg: float = Field(..., description="Optimal daily feed quantity in kg for the entire flock")
    status_flag: Literal["NORMAL", "LOW", "HIGH"] = Field(..., description="Under/Over feeding flag relative to expected breed weight curves")
    reasoning_explanation: str = Field(..., description="Plain language explanation and actionable advice for the farmer")
    confidence_level: Literal["HIGH", "MODERATE", "LOW"] = Field(..., description="Confidence of the prediction based on the input data")

from typing import List, Optional

class MortalityLogEntry(BaseModel):
    date: str = Field(..., description="Date of the log entry (YYYY-MM-DD)")
    count: int = Field(..., description="Number of birds that died on this date")
    cause: Optional[str] = Field(None, description="Reported cause of death, e.g., 'crushed', 'disease'")

class MortalityAnalysisRequest(BaseModel):
    flock_id: Optional[str] = Field(None, description="Internal Flock ID")
    breed: str = Field(..., description="Breed of the broiler")
    initial_bird_count: int = Field(..., description="Initial number of birds placed")
    current_bird_count: int = Field(..., description="Current number of active birds")
    recent_mortality: List[MortalityLogEntry] = Field(..., description="List of daily mortality records for analysis")

class MortalityAnalysisResponse(BaseModel):
    alert_level: Literal["NORMAL", "WARNING", "CRITICAL"] = Field(..., description="Risk level assessing anomalies")
    threshold_exceeded: bool = Field(..., description="True if standard mortality buffers broke benchmark curves")
    cumulative_mortality_rate: float = Field(..., description="Aggregated mortality rate in percentage")
    potential_causes: List[str] = Field(..., description="AI derived potential causes")
    recommendations: List[str] = Field(..., description="Actionable alerts or vaccine checks")
    confidence_score: float = Field(..., description="Value bounded 0.0 - 1.0 reflecting analysis high fidelity")

# --- Capability 3: Harvest Readiness Prediction
class HarvestPredictionRequest(BaseModel):
    flock_age_days: int = Field(..., description="Age of the flock in days")
    current_avg_weight_kg: float = Field(..., description="Current average bird weight in kilograms")
    target_weight_kg: float = Field(..., description="Target weight before harvest (e.g., 2.2 kg)")
    breed: str = Field(..., description="Breed of the broiler")

class HarvestPredictionResponse(BaseModel):
    estimated_days_to_target: int = Field(..., description="Estimated days remaining to reach target weight")
    daily_gain_estimate_g: float = Field(..., description="Predicted daily weight gain in grams per bird")
    status_flag: Literal["ON_TRACK", "DELAYED", "AHEAD"] = Field(..., description="Growth curve alignment status")
    recommendations: List[str] = Field(..., description="Actionable advice for optimal finishing")

# --- Capability 4: Disease Risk Detection
class DiseaseRiskRequest(BaseModel):
    symptoms: List[str] = Field(..., description="List of observed symptoms (e.g., coughing, lethargy)")
    recent_vaccinations: List[str] = Field(..., description="List of recorded vaccinations")
    mortality_alert_level: str = Field("NORMAL", description="Existing Mortality threat level context")

class DiseaseRiskResponse(BaseModel):
    suspected_conditions: List[str] = Field(..., description="Potential diseases suspected by AI patterns")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(..., description="Threat matrix escalation status")
    missed_critical_vaccines: List[str] = Field(..., description="Critical schedule buffers missed")
    recommendations: List[str] = Field(..., description="Actionable isolation or Vet callback triggers")

# --- Capability 5: Feed Conversion Ratio (FCR) Insights
class FcrInsightsRequest(BaseModel):
    total_feed_consumed_kg: float = Field(..., description="Total aggregate feed consumed by flock so far")
    current_avg_weight_kg: float = Field(..., description="Current average weight of birds")
    initial_bird_count: int = Field(..., description="Initial bird placement count")
    current_bird_count: int = Field(..., description="Active bird count")

class FcrInsightsResponse(BaseModel):
    estimated_fcr: float = Field(..., description="Calculated Feed Conversion Ratio standard")
    benchmark_status: Literal["EXCELLENT", "GOOD", "POOR"] = Field(..., description="Status vs standard 1.6 - 1.9 index")
    cost_impact_explanation: str = Field(..., description="Economic summary relating FCR to feed waste")
    recommendations: List[str] = Field(..., description="Formulation or isolation tactics")

# --- Capability 6: General Chatbot
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(..., description="Actor role for conversation indexing")
    content: str = Field(..., description="Text prompt content")

class ChatRequest(BaseModel):
    message: str = Field(..., description="Latest user question")
    history: Optional[List[ChatMessage]] = Field(None, description="Recent conversation backlogs for memory buffers")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Structured safe answer content")
    actionable_highlights: List[str] = Field(..., description="Bullet point buffers highlighting action steps")
