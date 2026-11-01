import os
import json

def serialize_document(final_document):
    """
    Phase 4.1 - Serializable Document Builder
    Converts the Final AI Document into a serialization-friendly workbook model.
    Strips away all AI-specific metadata, computer vision bounds, and processing traces.
    """
    
    # Pre-flight check
    if final_document.get("document_status") != "READY_FOR_EXPORT":
        print("Warning: Attempting to serialize a document that is not READY_FOR_EXPORT.")
        
    workbook = {
        "worksheets": []
    }
    
    tables = final_document.get("tables", [])
    
    for idx, table in enumerate(tables):
        worksheet_name = f"Page_{idx + 1}"
        
        worksheet = {
            "name": worksheet_name,
            "rows": []
        }
        
        rows = table.get("rows", table.get("matrix", []))
        
        for row_idx, row_data in enumerate(rows):
            is_dict = isinstance(row_data, dict)
            cells = row_data.get("cells", []) if is_dict else row_data
            r_index = row_data.get("index", row_idx) if is_dict else row_idx
            
            serialized_row = {
                "index": r_index,
                "cells": []
            }
            
            for cell in cells:
                final_text = cell.get("final_result", {}).get("text")
                # Normalize null explicitly
                if final_text is None:
                    final_text = ""
                    
                serialized_cell = {
                    "row": cell.get("row", row_idx),
                    "column": cell.get("column", 0),
                    "value": final_text,
                    "rowspan": cell.get("rowspan", 1),
                    "colspan": cell.get("colspan", 1)
                }
                
                serialized_row["cells"].append(serialized_cell)
                
            worksheet["rows"].append(serialized_row)
            
        workbook["worksheets"].append(worksheet)
        
    serialized_document = {
        "workbook": workbook
    }
    
    # Save the Serialized Document Output
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "serialized_document.json"), "w") as f:
            json.dump(serialized_document, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug serialized_document.json: {e}")
        
    return serialized_document
