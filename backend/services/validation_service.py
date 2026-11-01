import os
import json
import copy

def validate_document(merged_document):
    """
    Phase 3.6 - Intelligent Conflict Resolution
    Deterministically compares OCR results with GPT review results 
    and selects the final document value based on strict rules.
    """
    # Create a deep copy to ensure immutability of the layout geometry and previous stages
    validated_document = copy.deepcopy(merged_document)
    
    stats = {
        "ocr_used": 0,
        "gpt_used": 0,
        "null_values": 0,
        "validation_failures": 0
    }
    
    def resolve_node(node):
        ocr = node.get("ocr", {})
        llm = node.get("llm_review")
        
        final_text = ""
        source = "OCR"
        decision_rule = "Rule_Unknown"
        
        # Rule 5: If OCR was explicitly empty
        if ocr.get("status") == "empty" or ocr.get("empty", False):
            final_text = None
            source = "null"
            decision_rule = "Rule_5_Empty_OCR"
            stats["null_values"] += 1
            
        # Rule 1: If no LLM review exists (or GPT failed)
        elif not llm or not llm.get("reviewed"):
            final_text = ocr.get("raw_text", "")
            source = "OCR"
            decision_rule = "GPT_Fallback_OCR"
            stats["ocr_used"] += 1
            
        # Rule 4: If GPT returned unreadable
        elif llm.get("correction_status") == "unreadable":
            final_text = ocr.get("raw_text", "")
            source = "OCR"
            decision_rule = "Rule_4_GPT_Unreadable"
            stats["ocr_used"] += 1
            
        # Rule 2: If GPT agrees with OCR (accepted)
        elif llm.get("correction_status") == "accepted":
            final_text = ocr.get("raw_text", "")
            source = "OCR"
            decision_rule = "Rule_2_GPT_Accepted"
            stats["ocr_used"] += 1
            
        # Rule 3: If GPT corrected OCR AND LLM confidence == high
        elif llm.get("correction_status") == "corrected" and llm.get("confidence") == "high":
            final_text = llm.get("corrected_text", "")
            source = "GPT"
            decision_rule = "Rule_3_GPT_High_Confidence"
            stats["gpt_used"] += 1
            
        # Fallback Rule: If GPT corrected but confidence is not high
        else:
            final_text = ocr.get("raw_text", "")
            source = "OCR (GPT low confidence fallback)"
            decision_rule = "Rule_Fallback_Low_Confidence"
            stats["ocr_used"] += 1
            stats["validation_failures"] += 1 # Flagged as a partial failure to fully resolve
            
        node["final_result"] = {
            "text": final_text,
            "source": source,
            "decision_rule": decision_rule,
            "validated": True
        }
        
        if "processing_trace" not in node:
            node["processing_trace"] = []
        node["processing_trace"].append("Validated")

    # 1. Resolve Metadata Regions
    for region in validated_document.get("metadata_regions", []):
        resolve_node(region)
        
    # 2. Resolve Table Cells
    for table in validated_document.get("tables", []):
        for row in table.get("matrix", []):
            for cell in row:
                resolve_node(cell)
                
    validated_document["validation_statistics"] = stats
    
    # Save the Validated Document Output
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "validated_document.json"), "w") as f:
            json.dump(validated_document, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug validated_document.json: {e}")
        
    return validated_document
