from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

from ml.openrouter_clients import get_advisory_client

def generate_advice(weather, soil, crop_recommendation, yield_prediction, question=None):
    """
    Generate agricultural advice using OpenRouter (Mistral 7B).
    """
    try:
        print(f"[ADVISORY DEBUG] Function called with weather={weather}, soil={soil}")
        client = get_advisory_client()
        print(f"[ADVISORY DEBUG] Client created successfully")
        
        # 1. Format Crops List
        crops = crop_recommendation.get("recommended_crops", [])
        crop_list_str = ", ".join(
            [f"{c['crop']} ({c['success_percentage']}%)" for c in crops]
        ) if crops else "None"

        # 2. Extract Yield Data
        yield_val = yield_prediction.get("expected_yield_ton_per_hectare", "N/A")
        yield_conf = yield_prediction.get("confidence", "N/A")

        # 3. Build System Prompt
        context_str = f"""
Weather:
- Min Temperature: {weather.get('temp_min', 'N/A')} °C
- Max Temperature: {weather.get('temp_max', 'N/A')} °C
- Humidity: {weather.get('humidity', 'N/A')} %
- Rainfall (last 7 days): {weather.get('rain_7d', 'N/A')} mm

Soil:
- pH: {soil.get('ph', 'N/A')}
- Organic Carbon: {soil.get('organic_carbon_pct', 'N/A')} %

ML Predictions:
- Recommended Crops: {crop_list_str}
- Estimated Yield: {yield_val} tons/hectare
- Yield Confidence: {yield_conf}
"""
        system_prompt = f"""You are FarmBot, an AI agricultural expert. 

STRICT RULE: You ONLY answer questions about agriculture, crops, farming, soil, weather, and the farm dashboard data provided below.
If the user asks about ANYTHING else (politics, general knowledge, celebrities, coding, etc.), you MUST refuse to answer.

Context Data:
{context_str}

Response Guidelines:
1. If the question is NOT agricultural, reply EXACTLY: "I specialize in farming advice only. Please ask about your crops or field conditions."
2. If the question IS agricultural, analyze the data and provide advice.
3. Keep response under 150 words.
4. Use simple, helpful language.

User Question:"""

        user_content = question if question else "Please provide an advisory based on the dashboard data."

        # 4. Call OpenRouter
        # mistralai/mistral-7b-instruct-v0.1 was removed from OpenRouter; use a current free model.
        response = client.chat.completions.create(
            model="deepseek/deepseek-v4-flash-0731:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        content = response.choices[0].message.content
        if not content:
            return "AI advisory couldn't be generated for this data. Please try again."

        return content.strip()

    except Exception as e:
        print(f"[ADVISORY ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return "AI advisory temporarily unavailable. Please try again later."
