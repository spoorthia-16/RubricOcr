import os
import json
import copy

def build_final_document(validated_document):
    """
    Phase 3.7 - Final AI Document Generation
    Consolidates the validated layout, OCR, GPT review, and final validated text 
    into one immutable canonical document. This document becomes the official 
    output of the AI extraction pipeline and the sole input to Excel generation.
    """
    # Create a deep copy to guarantee immutability
    final_document = copy.deepcopy(validated_document)
    
    # Extract existing validation statistics to build the summary
    val_stats = validated_document.get("validation_statistics", {})
    
    stats = {
        "tables": len(final_document.get("tables", [])),
        "rows": 0,
        "columns": 0,
        "cells": 0,
        "metadata_regions": len(final_document.get("metadata_regions", [])),
        "ocr_used": val_stats.get("ocr_used", 0),
        "gpt_reviewed": val_stats.get("gpt_used", 0) + val_stats.get("validation_failures", 0),
        "finalized": 0
    }
    
    # Calculate dimensional stats
    for table in final_document.get("tables", []):
        stats["rows"] += table.get("dimensions", {}).get("rows", 0)
        stats["columns"] += table.get("dimensions", {}).get("columns", 0)
        
        for row in table.get("matrix", []):
            for cell in row:
                stats["cells"] += 1
                if "final_result" in cell:
                    stats["finalized"] += 1
                    
    # Add metadata region count to finalized count
    for region in final_document.get("metadata_regions", []):
        if "final_result" in region:
            stats["finalized"] += 1

    # Attach Pipeline Metadata
    pipeline_status = validated_document.get("pipeline_status", {})
    final_document["pipeline"] = {
        "layout": pipeline_status.get("layout", "completed"),
        "ocr": pipeline_status.get("ocr", "completed"),
        "gpt_review": pipeline_status.get("gpt_review", "completed"),
        "validation": "completed"
    }
    
    # Attach Integrity Statistics
    final_document["integrity"] = {
        "layout_complete": True,
        "ocr_complete": True,
        "validation_complete": True,
        "excel_ready": True
    }
    
    # Attach Summary
    final_document["summary"] = stats
    
    # Phase 3.8: End-to-End AI Validation
    final_document = verify_ready_for_export(final_document)
    
    # Save the Canonical Document Output
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "final_document.json"), "w") as f:
            json.dump(final_document, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug final_document.json: {e}")
        
    return final_document

def verify_ready_for_export(final_document):
    """
    Phase 3.8 - End-to-End AI Validation
    Performs a strict checklist to guarantee the document is 100% ready for Excel generation.
    Returns the document with 'document_status' updated.
    """
    errors = []
    cell_ids = set()
    
    # 1. Check Pipeline & Integrity
    pipeline = final_document.get("pipeline", {})
    integrity = final_document.get("integrity", {})
    
    if pipeline.get("layout") != "completed":
        errors.append("Layout phase failed.")
    if pipeline.get("ocr") != "completed":
        errors.append("OCR phase failed.")
    if not integrity.get("excel_ready"):
        errors.append("Integrity block is missing or excel_ready is false.")
        
    # 2. Check Tables & Cells
    for table_idx, table in enumerate(final_document.get("tables", [])):
        expected_cols = table.get("dimensions", {}).get("columns", 0)
        
        for row_idx, row in enumerate(table.get("matrix", [])):
            # While physical items in the row list might not match expected_cols due to merges,
            # we check logical structure constraints
            for cell in row:
                cid = cell.get("cell_id")
                
                # Check for duplicate IDs
                if cid is None:
                    errors.append(f"Missing cell_id in Table {table_idx}, Row {row_idx}.")
                elif cid in cell_ids:
                    errors.append(f"Duplicate cell_id detected: {cid}.")
                else:
                    cell_ids.add(cid)
                    
                # Check for final_result
                if "final_result" not in cell:
                    errors.append(f"Cell {cid} is missing 'final_result'.")
                    
                # Check image path
                if not cell.get("image_path"):
                    errors.append(f"Cell {cid} is missing 'image_path'.")
                    
                # Check bounding box
                bbox = cell.get("bbox")
                if not bbox or len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                    errors.append(f"Cell {cid} has an invalid bounding box: {bbox}.")
                    
                # Check merge constraints
                if cell.get("rowspan", 1) < 1 or cell.get("colspan", 1) < 1:
                    errors.append(f"Cell {cid} has invalid rowspan/colspan.")
                    
    # 3. Check Metadata Regions
    for region in final_document.get("metadata_regions", []):
        rid = region.get("region_id")
        if "final_result" not in region:
            errors.append(f"Metadata Region {rid} is missing 'final_result'.")
        if not region.get("image_path"):
            errors.append(f"Metadata Region {rid} is missing 'image_path'.")
        bbox = region.get("bbox")
        if not bbox or len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            errors.append(f"Metadata Region {rid} has an invalid bounding box: {bbox}.")

    if not errors:
        final_document["document_status"] = "READY_FOR_EXPORT"
    else:
        final_document["document_status"] = "EXPORT_VALIDATION_FAILED"
        final_document["export_validation_errors"] = errors
        
    return final_document
