import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "https://openrouter.ai/api/v1"

def _get_key(specific_var: str) -> str:
    """Helper to get key: specific -> generic -> RuntimeError"""
    key = os.getenv(specific_var)
    if key:
        return key
    
    fallback = os.getenv("OPENROUTER_API_KEY")
    if fallback:
        return fallback
    
    raise RuntimeError(f"Missing API Key: {specific_var} or OPENROUTER_API_KEY must be set.")

def get_advisory_client() -> OpenAI:
    """Returns OpenAI client configured for Advisory (Model 3)"""
    api_key = _get_key("OPENROUTER_ADVISORY_API_KEY")
    return OpenAI(base_url=BASE_URL, api_key=api_key)

def get_chatbot_client() -> OpenAI:
    """Returns OpenAI client configured for Chatbot (Model 4)"""
    api_key = _get_key("OPENROUTER_CHATBOT_API_KEY")
    return OpenAI(base_url=BASE_URL, api_key=api_key)

# OpenRouter's free-tier catalog rotates constantly — models get deprecated
# or rate-limited with no notice. Try each in order and use the first that
# returns real content, instead of hardcoding a single model.
FREE_MODEL_CHAIN = [
    "cohere/north-mini-code:free",
    "inclusionai/ling-3.0-flash-sante:free",
    "nvidia/nemotron-3.5-lightning:free",
    "google/gemma-4-31b-it:free",
    "qwen/qwen3.8-27b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
]

def chat_completion_with_fallback(client: OpenAI, messages: list, temperature: float, max_tokens: int):
    """
    Try FREE_MODEL_CHAIN in order, returning the first response with real
    (non-empty) content. Raises the last error if every model fails.
    """
    last_error = None
    for model in FREE_MODEL_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content.strip()
            last_error = RuntimeError(f"{model} returned empty content")
        except Exception as e:
            print(f"[OPENROUTER FALLBACK] {model} failed: {type(e).__name__}: {e}")
            last_error = e
            continue

    raise last_error or RuntimeError("All fallback models failed")
