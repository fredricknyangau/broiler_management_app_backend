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
