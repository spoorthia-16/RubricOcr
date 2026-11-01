import os
import sys
import json
import time
from datetime import datetime
import openpyxl

# Ensure config path is available
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from config.export_config import (
        EXPORT_DIRECTORY, FILE_PREFIX,
        TIMESTAMP_FORMAT, OVERWRITE_EXISTING
    )
except ImportError:
    EXPORT_DIRECTORY = "exports"
    FILE_PREFIX = "rubric_export"
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    OVERWRITE_EXISTING = False

def write_excel(workbook_bundle, serialized_document, output_path=None):
    """
    Phase 4.7 - Excel Writer
    Persists the fully prepared workbook to disk as an .xlsx file.
    Performs file integrity verification by re-opening the file.
    Includes all 8 Enterprise Improvements.
    """
    overall_start_time = time.time()
    iso_start = datetime.utcnow().isoformat() + "Z"
    
    wb = workbook_bundle.get("workbook")
    worksheet_map = workbook_bundle.get("worksheet_map", {})
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    backend_root = os.path.abspath(os.path.join(base_dir, ".."))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    print("Saving workbook...")
    
    # 2. Automatic Export Directory
    if output_path is None:
        exports_dir = os.path.join(backend_root, EXPORT_DIRECTORY)
        os.makedirs(exports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        base_filename = f"{FILE_PREFIX}_{timestamp}"
        output_path = os.path.join(exports_dir, f"{base_filename}.xlsx")
        
        # 3. Safe Filename Handling
        if not OVERWRITE_EXISTING:
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(exports_dir, f"{base_filename}_{counter}.xlsx")
                counter += 1
                
    # Measure Save Time
    save_start = time.time()
    try:
        wb.save(output_path)
    except Exception as e:
        return {
            "status": "FAILED",
            "error": f"Failed to save workbook: {str(e)}"
        }
    save_time_ms = int((time.time() - save_start) * 1000)
    print("Workbook saved successfully.")
    
    # Basic File Integrity
    if not os.path.exists(output_path):
        return {"status": "FAILED", "error": "File does not exist after saving."}
        
    file_size = os.path.getsize(output_path)
    if file_size <= 0:
        return {"status": "FAILED", "error": "File size is 0 bytes."}
        
    print("Validating workbook...")
    validation_start = time.time()
    
    # 6. Integrity Validation by reopening
    try:
        print("--- DEBUG VALIDATION ---")
        serialized_wb = serialized_document.get("workbook", {})
        print("Serialized Workbook Object:", json.dumps(serialized_wb, indent=2)[:500], "...") # truncating for sanity
        
        expected_worksheets = serialized_wb.get("worksheets", [])
        print(f"len(serialized_document['workbook']['worksheets']): {len(expected_worksheets)}")
        
        verify_wb = openpyxl.load_workbook(output_path, read_only=True)
        
        actual_names = verify_wb.sheetnames
        print(f"len(openpyxl_workbook.sheetnames): {len(actual_names)}")
        print("------------------------")
        
        # Determine expected names from serialized document instead of worksheet_map
        expected_names = [ws.get("name") for ws in expected_worksheets]
        
        if len(expected_names) != len(actual_names):
            return {"status": "FAILED", "error": f"Worksheet count mismatch. Expected: {len(expected_names)}, Found: {len(actual_names)}"}
            
        total_populated_cells = 0
            
        for name in expected_names:
            if name not in actual_names:
                return {"status": "FAILED", "error": f"Missing worksheet in saved file: {name}"}
                
            ws = verify_wb[name]
            
            # Check not empty
            if ws.max_row == 1 and ws.max_column == 1 and ws.cell(row=1, column=1).value is None:
                return {"status": "FAILED", "error": f"Worksheet {name} appears entirely empty upon reload."}
                
            # Count populated cells (scanning up to max bounds to save memory/time)
            for r in ws.iter_rows(values_only=True):
                for val in r:
                    if val is not None and str(val).strip() != "":
                        total_populated_cells += 1
                        
        verify_wb.close()
        
    except Exception as e:
        return {
            "status": "FAILED",
            "error": f"Workbook corruption detected. Failed to reopen: {str(e)}"
        }
        
    validation_time_ms = int((time.time() - validation_start) * 1000)
    print("Validation successful.")
    print("Export complete.")
    
    total_time_ms = int((time.time() - overall_start_time) * 1000)
    size_kb = round(file_size / 1024.0, 2)
    iso_end = datetime.utcnow().isoformat() + "Z"
    
    # 4. Export Timing
    performance = {
        "save_time_ms": save_time_ms,
        "validation_time_ms": validation_time_ms,
        "total_time_ms": total_time_ms
    }
    
    # 7. Generate export report
    export_report = {
        "export": {
            "status": "SUCCESS",
            "path": output_path,
            "size_kb": size_kb,
            "worksheets": len(worksheet_map),
            "performance": performance
        }
    }
    
    # 5. Export Trace
    export_trace = {
        "started": iso_start,
        "finished": iso_end,
        "output_file": output_path,
        "status": "SUCCESS"
    }
    
    # 8. Export Manifest
    export_manifest = {
        "document_status": "READY_FOR_EXPORT",
        "excel_status": "SUCCESS",
        "output_file": output_path,
        "generated_at": iso_end,
        "engine": "openpyxl"
    }
    
    try:
        with open(os.path.join(debug_folder, "export_report.json"), "w") as f:
            json.dump(export_report, f, indent=4)
            
        with open(os.path.join(debug_folder, "export_trace.json"), "w") as f:
            json.dump(export_trace, f, indent=4)
            
        with open(os.path.join(debug_folder, "export_manifest.json"), "w") as f:
            json.dump(export_manifest, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug export files: {e}")
        
    return {
        "status": "SUCCESS",
        "file_path": output_path,
        "statistics": export_report["export"]
    }
