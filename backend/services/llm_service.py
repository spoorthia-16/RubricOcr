import os
import json
import base64
import requests
from dotenv import load_dotenv

def encode_image(image_path):
    """Encodes an image to a base64 string for the GPT Vision API."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_document(document, image_paths):
    """
    Sends the structured document data (cells/text/bboxes) alongside the 
    cropped table images to GPT-4o to reconstruct the table into a clean JSON format.
    """
    load_dotenv()
    
    # Try Azure first, fallback to standard OpenAI
    is_azure = os.getenv("AZURE_OPENAI_ENDPOINT") is not None
    
    if is_azure:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not found in environment variables.")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "interns-gpt-4.1")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip('/')
        api_url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        model_name = deployment
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        api_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        model_name = "gpt-4o"

    if isinstance(image_paths, str):
        image_paths = [image_paths]

    # Base64 encode all provided cropped images
    image_messages = []
    for img_path in image_paths:
        base64_image = encode_image(img_path)
        image_messages.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}"
            }
        })
    
    # Headers are set above
    
    # Instruct GPT on its specific role and output expectations
    system_prompt = (
        "You are an AI document understanding assistant.\n"
        "You receive:\n"
        "• the original page image\n"
        "• OCR results\n"
        "• detected table cells\n\n"
        "Your task:\n"
        "1. Understand the document.\n"
        "2. Identify the column that uniquely identifies each evaluated person (e.g., Student No, Intern ID, etc.).\n"
        "3. Identify all assessment criteria columns (do not hardcode specific headers like 'Appearance').\n"
        "4. Detect tables.\n"
        "5. Preserve layout.\n"
        "6. Preserve rows.\n"
        "7. Preserve columns.\n"
        "8. Never invent information.\n"
        "9. Return JSON only.\n\n"
        "Rules:\n"
        "1. Never create new rows.\n"
        "2. Never remove rows.\n"
        "3. Never merge adjacent rows.\n"
        "4. Never merge adjacent columns.\n"
        "5. Preserve table order.\n"
        "6. Preserve merged headers.\n"
        "7. If text is unreadable, return null.\n"
        "8. Never invent information.\n"
        "9. Keep every detected table.\n"
        "10. Return JSON only.\n"
        "11. OCR engines often fail on vertically written headers (e.g. outputting 'ppnce' instead of 'Appearance'). You MUST read the image to correct headers to their true English text.\n"
        "12. If a sequential serial number column exists (e.g., 1, 2, 3...) but numbers are missing from the OCR data, you MUST deduce and fill in the missing numbers based on the visual sequence.\n"
        "13. If OCR incorrectly merged adjacent column values into a single cell (e.g., outputting '114' instead of '11' and '4', or '1010' instead of '10' and '10'), you MUST split them into their proper columns based on the visual grid.\n"
        "14. Use the provided OCR text as a starting point, but the visual image is the ULTIMATE source of truth for layout, numbering, and headers.\n\n"
        "--- FEW-SHOT EXAMPLES ---\n"
        "Example 1: Practical Assessment Rubric\n"
        "Input context implies a student named 'Alice' with 'Appearance' scored 5.\n"
        "Expected JSON:\n"
        "{\n"
        "    \"document_type\": \"Practical Assessment Rubric\",\n"
        "    \"metadata\": {\"Learner Name\": \"Alice\", \"Date\": \"2023-10-01\"},\n"
        "    \"tables\": [{\n"
        "        \"title\": \"Assessment Criteria\",\n"
        "        \"headers\": [\"Criteria\", \"Max Score\", \"Awarded\"],\n"
        "        \"rows\": [\n"
        "            {\"cells\": {\"Criteria\": \"Appearance\", \"Max Score\": \"10\", \"Awarded\": \"5\"}}\n"
        "        ]\n"
        "    }]\n"
        "}\n\n"
        "Example 2: Internship Evaluation Sheet\n"
        "Input context implies intern 'Bob' evaluated on 'Communication'.\n"
        "Expected JSON:\n"
        "{\n"
        "    \"document_type\": \"Internship Evaluation Sheet\",\n"
        "    \"metadata\": {\"Intern Name\": \"Bob\", \"Company\": \"Tech Corp\"},\n"
        "    \"tables\": [{\n"
        "        \"title\": \"Performance Review\",\n"
        "        \"headers\": [\"Category\", \"Rating\", \"Comments\"],\n"
        "        \"rows\": [\n"
        "            {\"cells\": {\"Category\": \"Communication\", \"Rating\": \"Excellent\", \"Comments\": \"Very clear\"}}\n"
        "        ]\n"
        "    }]\n"
        "}\n"
        "--- END EXAMPLES ---\n\n"
        "You MUST output exactly in the following JSON structure, with absolutely no markdown formatting, explanations, or additional text:\n"
        "{\n"
        "    \"document_type\": \"\",\n"
        "    \"metadata\": {},\n"
        "    \"tables\": []\n"
        "}"
    )
    
    user_prompt = (
        f"Here is the raw OCR data extracted from the document:\n\n{json.dumps(document, indent=2)}\n\n"
        "Please analyze this data alongside the provided cropped table images and output the final reconstructed JSON."
    )

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ] + image_messages
            }
        ],
        "response_format": { "type": "json_object" },
        "max_tokens": 8000,
        "temperature": 0
    }

    print("Sending document and image to GPT...")
    
    response = requests.post(api_url, headers=headers, json=payload)
    response.raise_for_status()
    
    result_text = response.json()["choices"][0]["message"]["content"]
    
    # Strip any markdown formatting (e.g. ```json ... ```) that GPT might inject
    result_text = result_text.strip()
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    if result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
        
    return json.loads(result_text.strip())
