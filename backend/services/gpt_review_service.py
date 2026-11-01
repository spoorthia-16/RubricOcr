import os
import json
import base64
import requests
from dotenv import load_dotenv

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def build_review_prompt(review_item):
    """
    Phase 3.2 - Universal Vision Prompt Engineering
    Builds a deterministic, strict verification prompt for GPT-4.1 Vision.
    """
    import os
    import json
    
    region_type = review_item.get("region_type", "unknown")
    row = review_item.get("row", "N/A")
    column = review_item.get("column", "N/A")
    ocr_text = review_item.get("ocr", {}).get("raw_text", "")
    ocr_confidence = review_item.get("ocr", {}).get("confidence", 0.0)
    
    system_prompt = """You are a highly precise document verification engine.
Your sole purpose is to verify and correct Optical Character Recognition (OCR) results against an image crop.

STRICT RULES:
1. Never behave like a chatbot. Never converse.
2. Never explain your reasoning unless explicitly requested in the JSON 'reason' field.
3. Never invent missing text. Do not hallucinate missing letters.
4. Never guess completely unreadable characters. If the text is illegible, return an empty string.
5. Use the provided OCR text as the primary source of truth.
6. Use the image only to verify or correct the OCR text.
7. Preserve whitespace, casing, and formatting where meaningful.
8. You must return ONLY a valid JSON object matching the exact schema below.

EXPECTED JSON SCHEMA:
{
    "corrected_text": "string of the accurate text",
    "correction_status": "accepted | corrected | unreadable",
    "confidence": "high | medium | low",
    "reason": "short explanation"
}"""

    user_prompt = f"""--- REGION CONTEXT ---
Type: {region_type}
Position: Row {row}, Column {column}

--- CURRENT OCR RESULT ---
Raw Text: '{ocr_text}'
Confidence Score: {ocr_confidence}

Please verify this text against the attached image. Return only the JSON object."""

    # Save to debug files
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    with open(os.path.join(debug_folder, "gpt_prompt.txt"), "w") as f:
        f.write("=== SYSTEM PROMPT ===\n")
        f.write(system_prompt)
        f.write("\n\n=== USER PROMPT ===\n")
        f.write(user_prompt)
        
    prompt_payload = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }
    
    with open(os.path.join(debug_folder, "gpt_request.json"), "w") as f:
        json.dump(prompt_payload, f, indent=4)
        
    return system_prompt, user_prompt

def review_region(review_item):
    """
    Phase 3.3 - Single Region GPT Review
    Sends a single OCR crop to GPT-4o Vision, validates the schema response,
    and performs a textual comparison to detect corrections.
    """
    import time
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    start_time = time.time()
    
    response_data = {
        "corrected_text": "",
        "correction_status": "unreadable",
        "confidence": "low",
        "reason": "Initialization failed",
        "processing_time_ms": 0
    }
    
    # Validation is handled down below when checking is_azure
        
    image_path = review_item.get("image_path")
    if not image_path or not os.path.exists(image_path):
        response_data["reason"] = "Image file not found on disk"
        return response_data
        
    try:
        base64_image = encode_image_to_base64(image_path)
    except Exception as e:
        response_data["reason"] = f"Failed to encode image: {str(e)}"
        return response_data
        
    # Headers constructed dynamically below
    
    original_ocr_text = review_item.get("ocr", {}).get("raw_text", "")
    
    system_prompt, user_prompt = build_review_prompt(review_item)

    payload = {
        "model": "gpt-4.1",
        "response_format": { "type": "json_object" },
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
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300,
        "temperature": 0.0
    }
    
    try:
        from config import GPT_TIMEOUT
    except ImportError:
        GPT_TIMEOUT = 60
        
    # Try Azure first, fallback to standard OpenAI
    is_azure = os.getenv("AZURE_OPENAI_ENDPOINT") is not None
    
    if is_azure:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            response_data["reason"] = "AZURE_OPENAI_API_KEY missing"
            return response_data
            
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "interns-gpt-4.1")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip('/')
        api_url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        payload["model"] = deployment
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            response_data["reason"] = "OPENAI_API_KEY missing"
            return response_data
            
        api_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload["model"] = "gpt-4o"
        
    try:
        api_response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=GPT_TIMEOUT
        )
        
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        log_path = os.path.join(debug_folder, "gpt_raw_response.txt")
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"--- NEW GPT REQUEST ---\n")
            f.write(f"Status Code: {api_response.status_code}\n")
            f.write(f"Headers: {api_response.headers}\n")
            f.write(f"Body: {api_response.text}\n\n")
            
        api_response.raise_for_status()
        
        raw_text = api_response.text.strip()
        if not raw_text:
            raise ValueError("Empty response body from GPT API")
            
        try:
            result_json = json.loads(raw_text)
        except json.JSONDecodeError:
            raise ValueError(f"GPT API did not return valid JSON. Raw body logged.")
            
        gpt_content = result_json["choices"][0]["message"]["content"].strip()
        
        if gpt_content.startswith("```json"):
            gpt_content = gpt_content[7:]
        elif gpt_content.startswith("```"):
            gpt_content = gpt_content[3:]
        if gpt_content.endswith("```"):
            gpt_content = gpt_content[:-3]
        gpt_content = gpt_content.strip()
        
        if not gpt_content:
            raise ValueError("GPT returned an empty content string.")
            
        parsed_content = json.loads(gpt_content)
        
        # Validate schema strictly
        required_keys = ["corrected_text", "correction_status", "confidence", "reason"]
        for key in required_keys:
            if key not in parsed_content:
                raise ValueError(f"Missing required key in GPT response: {key}")
        
        response_data["corrected_text"] = parsed_content["corrected_text"]
        response_data["correction_status"] = parsed_content["correction_status"]
        response_data["confidence"] = parsed_content["confidence"]
        response_data["reason"] = parsed_content["reason"]
        
    except requests.exceptions.Timeout:
        response_data["reason"] = "GPT API Timeout"
    except requests.exceptions.RequestException as e:
        response_data["reason"] = f"API Request Failed: {str(e)}"
    except json.JSONDecodeError:
        response_data["reason"] = "Failed to parse GPT response as JSON"
    except ValueError as ve:
        response_data["reason"] = f"Schema Validation Failed: {str(ve)}"
    except Exception as e:
        response_data["reason"] = f"Unknown Error: {str(e)}"
        
    response_data["processing_time_ms"] = int((time.time() - start_time) * 1000)
    
    # Text Comparison Object
    gpt_text = response_data.get("corrected_text", "")
    changed = (gpt_text != original_ocr_text)
    
    comparison = {
        "ocr_text": original_ocr_text,
        "gpt_text": gpt_text,
        "changed": changed
    }
    
    # Save Debug Outputs
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "gpt_review_result.json"), "w") as f:
            json.dump(response_data, f, indent=4)
            
        with open(os.path.join(debug_folder, "gpt_comparison.json"), "w") as f:
            json.dump(comparison, f, indent=4)
            
        # Log raw response history
        debug_path = os.path.join(debug_folder, "gpt_raw_response.json")
        log_entry = {
            "region": review_item,
            "gpt_raw_reply": gpt_content if 'gpt_content' in locals() else None,
            "parsed_response": response_data,
            "comparison": comparison,
            "api_error": response_data["reason"] if response_data["confidence"] == "low" and "failed" in response_data["reason"].lower() else None
        }
        
        existing_logs = []
        if os.path.exists(debug_path):
            try:
                with open(debug_path, "r") as f:
                    existing_logs = json.load(f)
            except json.JSONDecodeError:
                existing_logs = []
                
        existing_logs.append(log_entry)
        
        with open(debug_path, "w") as f:
            json.dump(existing_logs, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug files: {e}")
        
    return response_data

def review_document(gpt_review_package):
    """
    Phase 3.4 - Batch GPT Review Orchestration
    Processes all regions from the GPT Review Package, managing retries,
    progress tracking, and error isolation.
    """
    import sys
    import time
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from config import GPT_BATCH_SIZE, GPT_MAX_RETRIES
    except ImportError:
        GPT_BATCH_SIZE = 10
        GPT_MAX_RETRIES = 3
        
    start_time = time.time()
    
    review_regions = gpt_review_package.get("review_regions", [])
    total_regions = len(review_regions)
    
    results = []
    
    api_stats = {
        "total_requests": total_regions,
        "successful_requests": 0,
        "failed_requests": 0,
        "retry_count": 0
    }
    
    timing_stats = []
    
    stats = {
        "total_regions": total_regions,
        "reviewed": 0,
        "successful": 0,
        "failed": 0,
        "processing_time_ms": 0
    }
    
    # Process in batches
    for i in range(0, total_regions, GPT_BATCH_SIZE):
        batch = review_regions[i:i + GPT_BATCH_SIZE]
        
        for region in batch:
            stats["reviewed"] += 1
            
            attempt = 0
            success = False
            result = None
            
            while attempt <= GPT_MAX_RETRIES and not success:
                result = review_region(region)
                
                # Check for network/timeout/rate limit errors
                # A successful structural response or a hard image load error is NOT a network retry.
                reason = result.get("reason", "").lower()
                is_retryable = ("timeout" in reason or "api request failed" in reason or "rate limit" in reason)
                
                if result.get("confidence") != "low" or not is_retryable:
                    success = True
                else:
                    attempt += 1
                    api_stats["retry_count"] += 1
                    if attempt <= GPT_MAX_RETRIES:
                        print(f"  -> Retry {attempt}/{GPT_MAX_RETRIES} for Region (Reason: {reason})")
                        time.sleep(2) # Backoff
            
            p_time = result.get("processing_time_ms", 0)
            if p_time > 0:
                timing_stats.append(p_time)
                
            region_label = region.get('region_id') or region.get('cell_id', 'unknown')
            
            if success and result.get("confidence") != "low" and "failed" not in result.get("reason", "").lower():
                stats["successful"] += 1
                api_stats["successful_requests"] += 1
                print(f"Reviewing {stats['reviewed']}/{total_regions} (Region ID: {region_label}) [SUCCESS]")
            else:
                stats["failed"] += 1
                api_stats["failed_requests"] += 1
                print(f"Reviewing {stats['reviewed']}/{total_regions} (Region ID: {region_label}) [FAILED]")
                
            results.append({
                "region_type": region.get("region_type"),
                "table_id": region.get("table_id"),
                "cell_id": region.get("cell_id"),
                "region_id": region.get("region_id"),
                "gpt_response": result
            })
            
    stats["processing_time_ms"] = int((time.time() - start_time) * 1000)
    
    avg_latency = sum(timing_stats) / len(timing_stats) if timing_stats else 0
    min_latency = min(timing_stats) if timing_stats else 0
    max_latency = max(timing_stats) if timing_stats else 0
    
    analytics = {
        "api_statistics": api_stats,
        "timing": {
            "average_latency_ms": int(avg_latency),
            "fastest_request_ms": min_latency,
            "slowest_request_ms": max_latency
        }
    }
    
    document_review = {
        "document_review": stats,
        "analytics": analytics,
        "results": results
    }
    
    # Save the Final Orchestrated Review Outputs
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "gpt_document_review.json"), "w") as f:
            json.dump(document_review, f, indent=4)
            
        with open(os.path.join(debug_folder, "gpt_batch_log.json"), "w") as f:
            json.dump({"batch_stats": stats, "batch_size": GPT_BATCH_SIZE, "max_retries": GPT_MAX_RETRIES}, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write batch review outputs: {e}")
        
    return document_review
