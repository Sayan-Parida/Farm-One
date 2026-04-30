import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
BASE_URL = "https://openrouter.ai/api/v1"

def main():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY not set in environment/.env")
        return

    client = OpenAI(base_url=BASE_URL, api_key=api_key)
    try:
        models = client.models.list()
        print("Available models/endpoints:")
        for m in models.data:
            print(m.id)
    except Exception as e:
        print("Error listing models:", e)

if __name__ == '__main__':
    main()
