import os
import sys
import time

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
    ENABLE_LLM_CORRECTION,
)
from llm.client import LLMClient


def test_azure_connection():
    print("========== AZURE OPENAI CONFIGURATION ==========")
    print(f"AZURE_OPENAI_API_KEY     : {'Loaded' if AZURE_OPENAI_API_KEY else 'MISSING'}")
    print(f"AZURE_OPENAI_ENDPOINT    : {AZURE_OPENAI_ENDPOINT}")
    print(f"AZURE_OPENAI_DEPLOYMENT  : {AZURE_OPENAI_DEPLOYMENT}")
    print(f"AZURE_OPENAI_API_VERSION : {AZURE_OPENAI_API_VERSION}")
    print(f"ENABLE_LLM_CORRECTION    : {ENABLE_LLM_CORRECTION}")
    print("=================================================\n")

    if not AZURE_OPENAI_API_KEY:
        print("[ERROR] AZURE_OPENAI_API_KEY is missing. Please set it in backend/.env")
        return

    print("Sending test 'Hello' message to Azure OpenAI...")
    client = LLMClient()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! Reply with a single short greeting."},
    ]

    start_time = time.time()
    try:
        response_meta = client.chat_with_metadata(messages)
        duration = time.time() - start_time

        content = response_meta.get("content", "").strip()
        tokens = response_meta.get("tokens", {})

        print("\n========== TEST RESPONSE ==========")
        print(f"Deployment          : {AZURE_OPENAI_DEPLOYMENT}")
        print(f"Response Content    : {content}")
        print(f"Latency             : {response_meta.get('latency', round(duration, 2))} sec")
        print(f"Input Tokens        : {tokens.get('input_tokens', 0)}")
        print(f"Output Tokens       : {tokens.get('output_tokens', 0)}")
        print(f"Total Tokens        : {tokens.get('total_tokens', 0)}")
        print("===================================\n")

        if content:
            print("Connection Successful")
        else:
            print("Connection Failed: Empty response received from Azure OpenAI")

    except Exception as e:
        print(f"\n[CONNECTION ERROR] Azure OpenAI test failed: {e}")


if __name__ == "__main__":
    test_azure_connection()
