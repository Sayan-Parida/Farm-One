from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

from ml.openrouter_clients import get_chatbot_client

SYSTEM_PROMPT = """You are FarmBot, an agriculture-only assistant.

Rules:
- You answer ONLY questions related to agriculture, farming, crops, soil, weather, and yield.
- If a question is unrelated, respond with:
  'I can help only with agriculture and farming-related questions.'
- Do NOT answer unrelated questions even if you know the answer.
- Do NOT mention policies.
- Do NOT provide chemical dosages or medical advice.
- Keep answers factual, concise, and practical."""

def get_chat_response(question: str) -> str:
    """
    Generate a response from FarmBot (Agriculture only) using OpenRouter (Llama 3.1 8B).
    """
    try:
        client = get_chatbot_client()

        # Use the same reliable Mistral model used elsewhere if available.
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct-v0.1",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            temperature=0.2,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        # Log the error to help debugging during development
        print(f"[FARMBOT ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return "FarmBot is temporarily unavailable. Please try again later."
