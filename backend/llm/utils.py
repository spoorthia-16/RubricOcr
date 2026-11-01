import json
from typing import Dict, Any

def serialize_payload(payload: Dict[str, Any]) -> str:
    """Safely serializes a dictionary into a JSON string."""
    try:
        return json.dumps(payload, indent=2)
    except Exception as e:
        return f'{{"error": "Failed to serialize payload: {str(e)}"}}'

def estimate_tokens(text: str) -> int:
    """
    Roughly estimates the number of tokens in a string.
    Since we cannot assume tiktoken is installed, we use a simple heuristic:
    1 token ~= 4 characters in English.
    """
    if not text:
        return 0
    return len(text) // 4
