import openai
import os
import re
import json
import os
import openai

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()
import openai

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

client = openai.OpenAI(api_key=api_key)


def chat_with_llm(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful scheduler assistant. Only respond with JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    return content

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
