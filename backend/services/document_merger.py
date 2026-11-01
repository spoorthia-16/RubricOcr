import os
import json
import copy
from datetime import datetime

def merge_gpt_results(ocr_document, gpt_document_review):
    """
    Phase 3.5 - Merge GPT Corrections
    Merges GPT review results back into the OCR document.
    Preserves both the original OCR output and the GPT review output without discarding information.
    """
    # Create a deep copy to ensure immutability of the original layout
    merged_document = copy.deepcopy(ocr_document)
    
    gpt_results = gpt_document_review.get("results", [])
    
    # Pre-index GPT results for fast O(1) lookup
    metadata_map = {}
    cell_map = {}
    
    for res in gpt_results:
        rtype = res.get("region_type")
        if rtype == "metadata":
            region_id = res.get("region_id")
            if region_id is not None:
                metadata_map[region_id] = res
        elif rtype == "cell":
            table_id = res.get("table_id")
            cell_id = res.get("cell_id")
            if table_id is not None and cell_id is not None:
                cell_map[(table_id, cell_id)] = res
                
    stats = {
        "regions_reviewed": 0,
        "regions_changed": 0,
        "regions_accepted": 0
    }
    
    def apply_llm_review(node, gpt_data):
        stats["regions_reviewed"] += 1
        
        gpt_response = gpt_data.get("gpt_response", {})
        
        # Calculate if the text changed
        original_text = node.get("ocr", {}).get("raw_text", "")
        corrected_text = gpt_response.get("corrected_text", "")
        
        if corrected_text != original_text and gpt_response.get("confidence") != "failed":
            stats["regions_changed"] += 1
        else:
            stats["regions_accepted"] += 1
            
        node["llm_review"] = {
            "reviewed": True,
            "corrected_text": corrected_text,
            "correction_status": gpt_response.get("correction_status", "unreadable"),
            "confidence": gpt_response.get("confidence", "low"),
            "reason": gpt_response.get("reason", ""),
            "review_timestamp": datetime.utcnow().isoformat() + "Z",
            "model": "gpt-4o"
        }
        
        if "processing_trace" not in node:
            node["processing_trace"] = []
        node["processing_trace"].append("GPT reviewed")

    # 1. Merge into Metadata Regions
    for region in merged_document.get("metadata_regions", []):
        region_id = region.get("region_id")
        if region_id in metadata_map:
            apply_llm_review(region, metadata_map[region_id])
            
    # 2. Merge into Table Cells
    for table in merged_document.get("tables", []):
        table_id = table.get("table_id")
        for row in table.get("matrix", []):
            for cell in row:
                cell_id = cell.get("cell_id")
                if (table_id, cell_id) in cell_map:
                    apply_llm_review(cell, cell_map[(table_id, cell_id)])
                    
    merged_document["merge_statistics"] = stats
    
    # Save the Merged Document Output
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "merged_document.json"), "w") as f:
            json.dump(merged_document, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug merged_document.json: {e}")
        
    return merged_document
