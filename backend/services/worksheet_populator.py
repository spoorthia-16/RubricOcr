import os
import json

def _convert_value(value):
    """
    Intelligently detects cell values and casts them to native python types
    so that Excel natively recognizes numbers.
    """
    if value is None or value == "":
        return ""
        
    val_str = str(value).strip()
    
    # Filter out common OCR noise characters (strikeouts, dashes, dots)
    noise_chars = {"-", "x", "X", "/", "\\", "↑", "_", ".", ",", "~", "|", "—", "–"}
    if val_str in noise_chars:
        return ""
        
    
    # Try integer
    if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
        try:
            return int(val_str)
        except ValueError:
            pass
            
    # Try float
    try:
        return float(val_str)
    except ValueError:
        pass
        
    return val_str

def populate_workbook(workbook_bundle, serialized_document):
    """
    Phase 4.3 - Worksheet Populator
    Populates every worksheet using the serialized document.
    Writes cell values using 1-based indexing. Does not merge cells or style them.
    Includes Coordinate Verification, Duplicate Detection, and Cell Type Preservation.
    """
    
    wb = workbook_bundle.get("workbook")
    worksheet_map = workbook_bundle.get("worksheet_map", {})
    
    stats = {
        "worksheets": 0,
        "rows_written": 0,
        "cells_written": 0,
        "empty_cells": 0
    }
    
    population_trace = []
    
    worksheets_data = serialized_document.get("workbook", {}).get("worksheets", [])
    
    for ws_data in worksheets_data:
        ws_name = ws_data.get("name")
        ws = worksheet_map.get(ws_name)
        
        if not ws:
            print(f"Warning: Worksheet {ws_name} found in serialized document but missing in workbook bundle.")
            continue
            
        print(f"Populating worksheet: {ws_name}")
        stats["worksheets"] += 1
        
        written_cells = set()
        expected_cell_count = 0
        written_cell_count = 0
        
        ws_trace = {
            "worksheet": ws_name,
            "written_cells": []
        }
        
        rows = ws_data.get("rows", [])
        total_rows = len(rows)
        
        for row_idx, row_data in enumerate(rows):
            print(f"Writing row {row_idx + 1}/{total_rows}")
            stats["rows_written"] += 1
            
            cells = row_data.get("cells", [])
            for cell in cells:
                expected_cell_count += 1
                
                r = cell.get("row", -1)
                c = cell.get("column", -1)
                
                # 1. Coordinate Verification
                if r < 0 or c < 0:
                    print(f"Warning: Rejecting invalid coordinates (Row: {r}, Col: {c})")
                    continue
                    
                # 2. Duplicate Cell Detection
                coord = (r, c)
                if coord in written_cells:
                    print(f"Warning: Duplicate cell detected at (Row: {r}, Col: {c}). Skipping overwrite.")
                    continue
                    
                written_cells.add(coord)
                
                raw_value = cell.get("value", "")
                
                # 6. Cell Type Preservation
                converted_value = _convert_value(raw_value)
                
                if converted_value == "":
                    stats["empty_cells"] += 1
                    
                # openpyxl uses 1-based indexing for rows and columns
                excel_row = r + 1
                excel_col = c + 1
                
                ws.cell(row=excel_row, column=excel_col, value=converted_value)
                
                written_cell_count += 1
                stats["cells_written"] += 1
                
                # 3. Population Trace
                ws_trace["written_cells"].append({
                    "row": r,
                    "column": c,
                    "value": converted_value
                })
                
        print(f"Worksheet {ws_name} completed.")
        population_trace.append(ws_trace)
        
        # 5. Data Integrity Check
        if written_cell_count != expected_cell_count:
            print(f"Warning: Population mismatch detected in {ws_name}. Expected: {expected_cell_count}, Written: {written_cell_count}")
            
    # Save the Statistics and Trace
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "worksheet_population.json"), "w") as f:
            json.dump({"population_statistics": stats}, f, indent=4)
            
        with open(os.path.join(debug_folder, "population_trace.json"), "w") as f:
            json.dump(population_trace, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug files: {e}")
        
    return {
        "workbook": wb,
        "statistics": stats
    }
