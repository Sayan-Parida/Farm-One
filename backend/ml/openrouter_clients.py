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
