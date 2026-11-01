import os
import sys
import json
from openpyxl.utils import get_column_letter

# Ensure config path is available
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from config.excel_dimensions import (
        MIN_COLUMN_WIDTH, MAX_COLUMN_WIDTH,
        MIN_ROW_HEIGHT, MAX_ROW_HEIGHT,
        CHARACTER_WIDTH_FACTOR, ROW_HEIGHT_PER_LINE
    )
except ImportError:
    # Fallback if config is missing
    MIN_COLUMN_WIDTH = 8
    MAX_COLUMN_WIDTH = 40
    MIN_ROW_HEIGHT = 18
    MAX_ROW_HEIGHT = 80
    CHARACTER_WIDTH_FACTOR = 1.2
    ROW_HEIGHT_PER_LINE = 18

def adjust_dimensions(workbook_bundle):
    """
    Phase 4.6 - Dimension Manager
    Automatically optimizes worksheet dimensions based on the final workbook contents.
    Incorporates 8 Enterprise Improvements (Centralized Config, Smart Widths, Merge Awareness, 
    Clamping, Traces, Validation, etc.)
    """
    print("Adjusting dimensions...")
    wb = workbook_bundle.get("workbook")
    worksheet_map = workbook_bundle.get("worksheet_map", {})
    
    stats = {
        "worksheets": 0,
        "columns_adjusted": 0,
        "rows_adjusted": 0,
        "widest_column": "A",
        "tallest_row": 1,
        "max_width_found": 0,
        "max_height_found": 0
    }
    
    dimension_trace = []
    validation_summary = []
    
    for ws_name, ws in worksheet_map.items():
        print(f"Adjusting worksheet: {ws_name}")
        stats["worksheets"] += 1
        
        ws_trace = {
            "worksheet": ws_name,
            "columns": [],
            "rows": []
        }
        
        ws_validation = {
            "worksheet": ws_name,
            "errors": []
        }
        
        column_widths = {}
        row_heights = {}
        
        total_cols = ws.max_column
        total_rows = ws.max_row
        
        # Determine which cells are part of a merge (to ignore non-top-left width calculations)
        merged_cells = []
        for merge_range in ws.merged_cells.ranges:
            merged_cells.append(merge_range)
            
        # O(1) single pass lookup for width and height constraints
        for r_idx in range(1, total_rows + 1):
            # Track multiline requirements for row height
            max_lines_in_row = 1
            
            for c_idx in range(1, total_cols + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                val = cell.value
                
                # Check if this cell is inside a merge but NOT the top-left cell
                is_merged_subcell = False
                for m_range in merged_cells:
                    if cell.coordinate in m_range:
                        if m_range.min_row != r_idx or m_range.min_col != c_idx:
                            is_merged_subcell = True
                        break
                        
                if val is not None and str(val).strip() != "":
                    # Intelligent calculation
                    text = str(val).rstrip()
                    lines = text.split("\n")
                    
                    # Update row lines estimate
                    if len(lines) > max_lines_in_row:
                        max_lines_in_row = len(lines)
                        
                    # Update column width (ignore if it's a hidden merged subcell)
                    if not is_merged_subcell:
                        longest_line = max(len(line) for line in lines)
                        calc_width = longest_line * CHARACTER_WIDTH_FACTOR
                        
                        col_letter = get_column_letter(c_idx)
                        if calc_width > column_widths.get(col_letter, 0):
                            column_widths[col_letter] = calc_width
                            
            # Calculate row height
            calc_height = max_lines_in_row * ROW_HEIGHT_PER_LINE
            if calc_height > row_heights.get(r_idx, 0):
                row_heights[r_idx] = calc_height
                
        # Apply Column Dimensions
        col_processed = 0
        for col_letter, raw_width in column_widths.items():
            col_processed += 1
            
            # Outlier Detection & Clamping
            applied_width = raw_width
            if applied_width > MAX_COLUMN_WIDTH:
                print(f"Column {col_letter} exceeded maximum width. Calculated: {applied_width:.1f}, Applied: {MAX_COLUMN_WIDTH}")
                applied_width = MAX_COLUMN_WIDTH
            elif applied_width < MIN_COLUMN_WIDTH:
                applied_width = MIN_COLUMN_WIDTH
                
            ws.column_dimensions[col_letter].width = applied_width
            stats["columns_adjusted"] += 1
            
            if applied_width > stats["max_width_found"]:
                stats["max_width_found"] = applied_width
                stats["widest_column"] = col_letter
                
            ws_trace["columns"].append({"column": col_letter, "width": applied_width})
            
            # Progress Logging
            if col_processed % 5 == 0 or col_processed == len(column_widths):
                print(f"Columns processed: {col_processed}/{len(column_widths)}")
                
        # Apply Row Dimensions
        row_processed = 0
        for r_idx, raw_height in row_heights.items():
            # Ignore empty rows (default to 0 in our logic or no value)
            if raw_height <= 0:
                continue
                
            row_processed += 1
            
            # Outlier Detection & Clamping
            applied_height = raw_height
            if applied_height > MAX_ROW_HEIGHT:
                print(f"Row {r_idx} exceeded maximum height. Calculated: {applied_height}, Applied: {MAX_ROW_HEIGHT}")
                applied_height = MAX_ROW_HEIGHT
            elif applied_height < MIN_ROW_HEIGHT:
                applied_height = MIN_ROW_HEIGHT
                
            ws.row_dimensions[r_idx].height = applied_height
            stats["rows_adjusted"] += 1
            
            if applied_height > stats["max_height_found"]:
                stats["max_height_found"] = applied_height
                stats["tallest_row"] = r_idx
                
            ws_trace["rows"].append({"row": r_idx, "height": applied_height})
            
            # Progress Logging
            if row_processed % 10 == 0 or row_processed == len(row_heights):
                print(f"Rows processed: {row_processed}/{len(row_heights)}")
                
        print("Worksheet completed.")
        dimension_trace.append(ws_trace)
        
        # 8. Dimension Integrity Validation
        for col_letter, final_w in column_widths.items():
            actual_w = ws.column_dimensions[col_letter].width
            if actual_w < MIN_COLUMN_WIDTH or actual_w > MAX_COLUMN_WIDTH:
                ws_validation["errors"].append(f"Column {col_letter} width ({actual_w}) out of bounds.")
                
        for r_idx, final_h in row_heights.items():
            actual_h = ws.row_dimensions[r_idx].height
            if actual_h < MIN_ROW_HEIGHT or actual_h > MAX_ROW_HEIGHT:
                ws_validation["errors"].append(f"Row {r_idx} height ({actual_h}) out of bounds.")
                
        validation_summary.append(ws_validation)
        
    # Save the Statistics and Traces
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        with open(os.path.join(debug_folder, "dimension_report.json"), "w") as f:
            json.dump({"dimension_statistics": stats}, f, indent=4)
            
        with open(os.path.join(debug_folder, "dimension_trace.json"), "w") as f:
            json.dump(dimension_trace, f, indent=4)
            
        with open(os.path.join(debug_folder, "dimension_validation.json"), "w") as f:
            json.dump(validation_summary, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug dimension files: {e}")
        
    return workbook_bundle
