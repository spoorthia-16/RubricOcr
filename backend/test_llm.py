import os
import requests
from dotenv import load_dotenv

def test_llm():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Say Hello"}
        ],
        "max_tokens": 10
    }

    print("Sending request to GPT...")
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        
        reply = response.json()["choices"][0]["message"]["content"]
        print(f"GPT Reply: {reply}")
        
        if "hello" in reply.lower():
            print("Success! GPT is working perfectly.")
        else:
            print("GPT responded, but didn't say Hello.")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to GPT: {e}")
        if response is not None:
            print(f"Response details: {response.text}")

if __name__ == "__main__":
    test_llm()
