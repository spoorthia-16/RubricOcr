import json
import os

def validate_ocr_document(ocr_document):
    """
    Phase 2.5.1 - OCR Validation Framework
    Analyzes the OCR document generated in Phase 2.4 to calculate detailed metrics.
    Does not modify the original document.
    """
    total_metadata_regions = 0
    total_table_cells = 0
    
    successful = 0
    failed = 0
    empty = 0
    needs_review = 0
    
    confidences = []
    
    def process_ocr_data(ocr_data):
        nonlocal successful, failed, empty, needs_review
        
        if not ocr_data:
            failed += 1
            return
            
        if ocr_data.get("empty", False):
            empty += 1
            return
            
        text = ocr_data.get("raw_text", "").strip()
        conf = ocr_data.get("confidence", 0.0)
        
        if ocr_data.get("needs_review", False) or text == "" or "[OCR FAILED]" in text or "[UNREADABLE" in text:
            needs_review += 1
        else:
            successful += 1
            
        if conf > 0:
            confidences.append(conf)

    # 1. Analyze Metadata Regions
    for region in ocr_document.get("metadata_regions", []):
        total_metadata_regions += 1
        process_ocr_data(region.get("ocr"))

    # 2. Analyze Table Cells
    for table in ocr_document.get("tables", []):
        for row in table.get("matrix", []):
            for cell in row:
                total_table_cells += 1
                process_ocr_data(cell.get("ocr"))
                
    total_regions = total_metadata_regions + total_table_cells
    
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    min_conf = min(confidences) if confidences else 0.0
    max_conf = max(confidences) if confidences else 0.0
    
    validation_results = {
        "summary": {
            "total_regions": total_regions,
            "total_metadata_regions": total_metadata_regions,
            "total_table_cells": total_table_cells,
            "successful": successful,
            "failed": failed,
            "empty": empty,
            "needs_review": needs_review,
            "average_confidence": round(avg_conf, 3),
            "min_confidence": round(min_conf, 3),
            "max_confidence": round(max_conf, 3)
        }
    }
    
    # Save the Validation Output
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    with open(os.path.join(debug_folder, "ocr_validation.json"), "w") as f:
        json.dump(validation_results, f, indent=4)
        
    return validation_results

def classify_ocr_regions(ocr_document):
    """
    Phase 2.5.2 - Cell-Level OCR Classification
    Classifies every OCR result using confidence thresholds to prepare the document for intelligent routing.
    """
    import copy
    
    # Do not import at the top level to avoid circular imports if config is complex
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from config import HIGH_CONFIDENCE_THRESHOLD, REVIEW_THRESHOLD
    except ImportError:
        HIGH_CONFIDENCE_THRESHOLD = 0.85
        REVIEW_THRESHOLD = 0.60
        
    # We mutate a copy of the document or modify in place? The instructions say "Update every OCR node"
    # and return statistics, saving the updated document to `ocr_classification.json`.
    classified_doc = copy.deepcopy(ocr_document)
    
    stats = {
        "accepted": 0,
        "review": 0,
        "failed": 0,
        "empty": 0
    }
    
    def classify_node(ocr_data):
        if not ocr_data:
            return
            
        if ocr_data.get("empty", False):
            ocr_data["status"] = "empty"
            stats["empty"] += 1
            return
            
        conf = ocr_data.get("confidence", 0.0)
        
        if conf >= HIGH_CONFIDENCE_THRESHOLD:
            ocr_data["status"] = "accepted"
            stats["accepted"] += 1
        elif conf >= REVIEW_THRESHOLD:
            ocr_data["status"] = "review"
            stats["review"] += 1
        else:
            ocr_data["status"] = "failed"
            stats["failed"] += 1
            
    # Process metadata regions
    for region in classified_doc.get("metadata_regions", []):
        classify_node(region.get("ocr"))
        
    # Process table cells
    for table in classified_doc.get("tables", []):
        for row in table.get("matrix", []):
            for cell in row:
                classify_node(cell.get("ocr"))
                
    classified_doc["classification_statistics"] = stats
    
    # Save the Classification Output
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    with open(os.path.join(debug_folder, "ocr_classification.json"), "w") as f:
        json.dump(classified_doc, f, indent=4)
        
    return classified_doc

def build_gpt_review_package(classified_document):
    """
    Phase 2.5.3 - OCR Routing Package
    Prepares a subset of OCR regions that require GPT Vision review.
    Isolates 'review' and 'failed' nodes to prevent unnecessary token usage.
    """
    import os
    import json
    
    review_regions = []
    stats = classified_document.get("classification_statistics", {
        "accepted": 0, "review": 0, "failed": 0, "empty": 0
    })
    
    # Target regions that explicitly need review or failed
    target_statuses = ["review", "failed"]
    
    # 1. Scan Metadata Regions
    for region in classified_document.get("metadata_regions", []):
        ocr_data = region.get("ocr", {})
        if ocr_data.get("status") in target_statuses:
            review_regions.append({
                "region_type": "metadata",
                "region_id": region.get("region_id"),
                "type": region.get("type"),
                "image_path": region.get("image_path"),
                "ocr": ocr_data,
                "bbox": region.get("bbox")
            })
            
    # 2. Scan Table Cells
    for table in classified_document.get("tables", []):
        table_id = table.get("table_id")
        for row in table.get("matrix", []):
            for cell in row:
                ocr_data = cell.get("ocr", {})
                if ocr_data.get("status") in target_statuses:
                    review_regions.append({
                        "region_type": "cell",
                        "table_id": table_id,
                        "cell_id": cell.get("cell_id"),
                        "row": cell.get("row"),
                        "column": cell.get("column"),
                        "image_path": cell.get("image_path"),
                        "ocr": ocr_data,
                        "bbox": cell.get("bbox")
                    })
                    
    # 3. Assemble Review Package
    package = {
        "document_info": classified_document.get("document_info", {}),
        "routing_summary": {
            "accepted": stats.get("accepted", 0),
            "review": stats.get("review", 0),
            "failed": stats.get("failed", 0),
            "total_sent_to_gpt": len(review_regions)
        },
        "review_regions": review_regions
    }
    
    # 4. Save the Package Output
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    with open(os.path.join(debug_folder, "gpt_review_package.json"), "w") as f:
        json.dump(package, f, indent=4)
        
    return package
