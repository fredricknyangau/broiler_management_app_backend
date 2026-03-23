from fastapi import APIRouter, Depends, HTTPException
from app.schemas.ai import (
    FeedRecommendationRequest, 
    FeedRecommendationResponse,
    MortalityAnalysisRequest,
    MortalityAnalysisResponse,
    HarvestPredictionRequest,
    HarvestPredictionResponse,
    DiseaseRiskRequest,
    DiseaseRiskResponse,
    FcrInsightsRequest,
    FcrInsightsResponse,
    ChatRequest,
    ChatResponse
)
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

@router.post("/mortality-analysis", response_model=MortalityAnalysisResponse)
async def get_mortality_analysis(
    payload: MortalityAnalysisRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    2. Mortality analytics and spike detection
    Analyzes bird mortality logs to flag potential anomalies or risk vectors (e.g., thermal shock, disease).
    """
    provider = get_ai_provider()
    
    system_prompt = """
You are an expert East African poultry farming AI assistant specialized in mortality diagnostics for broilers.
Given the following daily mortality logs and flock state, analyze the cumulative and daily mortality rate.
Compare against acceptable broiler industry benchmarks (e.g. cumulative < 5% by day 42, daily spikes < 0.1%).
Identify any potential disease triggers, thermal shock risks, or management errors based on given causes.
Flag it if a threshold was exceeded.
Return your response STRICTLY as a JSON object matching the requested schema exactly.
"""

    user_prompt = f"""
Flock State:
- Breed: {payload.breed}
- Initial Birds: {payload.initial_bird_count}
- Current Birds: {payload.current_bird_count}

Recent Daily Mortality Logs:
{json.dumps([m.model_dump() for m in payload.recent_mortality], indent=2)}

Please analyze the spikes and generate a structured analytics report.
"""

    expected_schema = MortalityAnalysisResponse.model_json_schema()
    
    system_prompt += f"\n\nEXPECTED JSON SCHEMA:\n{json.dumps(expected_schema, indent=2)}"

    try:
        raw_json = await provider.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=expected_schema
        )
        return MortalityAnalysisResponse(**raw_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Integration Error: {str(e)}")

@router.post("/harvest-prediction", response_model=HarvestPredictionResponse)
async def get_harvest_prediction(
    payload: HarvestPredictionRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    3. Harvest Readiness Prediction
    Estimates remaining days to target weights basing off breed growth curves.
    """
    provider = get_ai_provider()
    system_prompt = """
You are an expert East African poultry farming AI assistant.
Compare the flock's current average weight against the target weight for the provided breed.
Calculate days remaining to target based on standard daily weight gain metrics (g/day) for this lifecycle stage.
Return response STRICTLY as a JSON object matching the requested schema.
"""
    user_prompt = f"""
Flock State:
- Breed: {payload.breed}
- Age: {payload.flock_age_days} days
- Current Weight: {payload.current_avg_weight_kg} kg
- Target Weight: {payload.target_weight_kg} kg
"""
    expected_schema = HarvestPredictionResponse.model_json_schema()
    system_prompt += f"\n\nEXPECTED JSON SCHEMA:\n{json.dumps(expected_schema, indent=2)}"

    try:
        raw_json = await provider.generate_structured_response(system_prompt, user_prompt, expected_schema)
        return HarvestPredictionResponse(**raw_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disease-risk", response_model=DiseaseRiskResponse)
async def detect_disease_risk(
    payload: DiseaseRiskRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    4. Disease Risk Detection
    Correlates symptoms and missed vaccines to flag potential outbreaks.
    """
    provider = get_ai_provider()
    system_prompt = """
You are an expert East African poultry vet AI assistant.
Analyze observed symptoms against common East African broiler diseases (NDV, IBD, Coccidiosis).
Evaluate risk level mapping vaccines reported.
Return response STRICTLY as a JSON object matching the requested schema.
"""
    user_prompt = f"""
Diagnostics:
- Symptoms: {", ".join(payload.symptoms)}
- Recent Vaccinations: {", ".join(payload.recent_vaccinations)}
- Mortality Risk: {payload.mortality_alert_level}
"""
    expected_schema = DiseaseRiskResponse.model_json_schema()
    system_prompt += f"\n\nEXPECTED JSON SCHEMA:\n{json.dumps(expected_schema, indent=2)}"

    try:
        raw_json = await provider.generate_structured_response(system_prompt, user_prompt, expected_schema, image_base64=payload.image_base64)
        return DiseaseRiskResponse(**raw_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fcr-insights", response_model=FcrInsightsResponse)
async def get_fcr_insights(
    payload: FcrInsightsRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    5. Feed Conversion Ratio Insights
    Tracks feed waste analytics and yields optimal profitability feedback lists.
    """
    provider = get_ai_provider()
    system_prompt = """
You are an expert East African poultry economics AI assistant.
Calculate the FCR = (Total Feed Consumed / Total Weight of current flock).
State whether FCR is EXCELLENT (<1.6), GOOD (1.6-1.9), or POOR (>1.9).
Explain cost impact scaling.
Return response STRICTLY as a JSON object matching the requested schema.
"""
    total_estimated_mass = payload.current_avg_weight_kg * payload.current_bird_count
    user_prompt = f"""
Stats:
- Total Feed Consumed: {payload.total_feed_consumed_kg} kg
- Total Flock Mass (est): {total_estimated_mass} kg ({payload.current_avg_weight_kg}kg * {payload.current_bird_count} birds)
"""
    expected_schema = FcrInsightsResponse.model_json_schema()
    system_prompt += f"\n\nEXPECTED JSON SCHEMA:\n{json.dumps(expected_schema, indent=2)}"

    try:
        raw_json = await provider.generate_structured_response(system_prompt, user_prompt, expected_schema)
        return FcrInsightsResponse(**raw_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def get_ai_chat(
    payload: ChatRequest,
    current_user: Any = Depends(get_current_user)
):
    """
    6. General Conversational Advice
    Safety conversational buffer housing East-African contextual memory buffers.
    """
    provider = get_ai_provider()
    system_prompt = """
You are a helpful East African poultry farming expert.
Provide safe, practical advice for raising broilers securely.
Return response STRICTLY as a JSON object matching the requested schema.
"""
    user_prompt = payload.message
    if payload.history:
         # Optionally inject history into prompt context for memory buffering
         hist_str = "\n".join([f"{h.role.upper()}: {h.content}" for h in payload.history])
         user_prompt = f"Chat History:\n{hist_str}\n\nUser: {payload.message}"

    expected_schema = ChatResponse.model_json_schema()
    system_prompt += f"\n\nEXPECTED JSON SCHEMA:\n{json.dumps(expected_schema, indent=2)}"

    try:
        raw_json = await provider.generate_structured_response(system_prompt, user_prompt, expected_schema)
        return ChatResponse(**raw_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
