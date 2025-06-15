import os
import re
import json
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get Google API key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# Gemini API endpoint
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

def chat_with_llm(prompt):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"You are a helpful scheduler assistant. Only respond with JSON.\n{prompt}"}
                ]
            }
        ]
    }

    response = requests.post(GEMINI_URL, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Gemini API error: {response.status_code} {response.text}")

    data = response.json()
    # Extract the generated text
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return content
    except (KeyError, IndexError):
        return None

def extract_json_from_llm_response(llm_response):
    """
    Extract first JSON object from LLM response.
    """
    match = re.search(r'\{.*\}', llm_response, re.DOTALL)
    if match:
        json_text = match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None
    return None

# # Example usage:
# if __name__ == "__main__":
#     prompt = "Schedule a meeting with Alice tomorrow at 3 PM."
#     response_text = chat_with_llm(prompt)
#     print("Raw LLM response:", response_text)

#     json_data = extract_json_from_llm_response(response_text)
#     print("Extracted JSON:", json_data)
