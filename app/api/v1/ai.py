from fastapi import APIRouter, Depends, HTTPException
from app.schemas.ai import FeedRecommendationRequest, FeedRecommendationResponse
from app.services.ai.factory import get_ai_provider
from app.api.deps import get_current_user
from typing import Any
import json

router = APIRouter()

@router.post("/feed-recommendation", response_model=FeedRecommendationResponse)
async def get_feed_recommendation(
    payload: FeedRecommendationRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    1. Feed recommendations based on flock age and weight
    Given current age, avg weight, breed, and bird count, recommend optimal daily feed.
    """
    provider = get_ai_provider()
    
    system_prompt = """
You are an expert East African poultry farming AI assistant specialized in broiler management.
Given the following flock data, calculate the optimal daily feed requirement in kilograms for the entire flock.
Compare the current average weight against standard growth curves for the provided breed.
If the current weight implies significant underfeeding or overfeeding, flag it.
Return your response STRICTLY as a JSON object matching the requested schema exactly.
"""

    user_prompt = f"""
Flock Parameters:
- Age: {payload.flock_age_days} days
- Current Avg Weight: {payload.current_avg_weight_kg} kg
- Breed: {payload.breed}
- Total Birds: {payload.bird_count}

Please analyze and generate the optimal daily feed in kilograms.
"""

    # The schema constraint for OpenAI's json_object parser
    expected_schema = FeedRecommendationResponse.model_json_schema()
    
    system_prompt += f"\n\nEXPECTED JSON SCHEMA:\n{json.dumps(expected_schema, indent=2)}"

    try:
        raw_json = await provider.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=expected_schema
        )
        
        # Pydantic automatic validation and conversion from the dictionary return
        return FeedRecommendationResponse(**raw_json)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Integration Error: {str(e)}")
