import copy
from typing import Dict, Any, List

class PatchApplier:
    """Applies validated LLM patches to an OCR Document safely."""
    
    def __init__(self, raw_document: Dict[str, Any]):
        # Deep copy to ensure raw_document is never overwritten
        self.corrected_document = copy.deepcopy(raw_document)
        self.diff_report = {"changes": []}
        
    def apply_patch(self, patch: Dict[str, Any]) -> bool:
        """Applies a single patch and records it in the diff report. Returns True if successful."""
        table_idx = patch.get("table_index", -1)
        row_idx = patch.get("row_index", -1)
        col_idx = patch.get("column_index", -1)
        new_val = patch.get("new_value", "")
        old_val = patch.get("old_value", "")
        reason = patch.get("reason", "Unknown")
        
        tables = self.corrected_document.get("tables", [])
        if not (0 <= table_idx < len(tables)):
            return False
            
        target_table = tables[table_idx]
        rows = target_table.get("rows", [])
        
        # We search by the actual row/col index defined in the data structure
        target_row = None
        for r in rows:
            if r.get("index") == row_idx:
                target_row = r
                break
                
        if not target_row:
            return False
            
        target_cell = None
        for c in target_row.get("cells", []):
            if c.get("column") == col_idx:
                target_cell = c
                break
                
        if not target_cell:
            return False
            
        # Optional: We could verify target_cell["value"] matches old_val here,
        # but OCR trailing spaces might cause mismatch. We apply blindly if indices match.
        actual_old = target_cell.get("value", "")
        target_cell["value"] = new_val
        
        self.diff_report["changes"].append({
            "path": f"tables[{table_idx}].rows[index={row_idx}].cells[col={col_idx}]",
            "before": actual_old,
            "after": new_val,
            "reason": reason
        })
        
        return True

class Postprocessor:
    """Orchestrates the patching of an OCR document and diff generation."""
    
    def __init__(self, raw_document: Dict[str, Any]):
        self.raw_document = raw_document
        self.applier = PatchApplier(raw_document)
        
    def apply_llm_response(self, response_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Iterates over the LLM response patch list and safely applies them."""
        patches = response_dict.get("patches", [])
        
        success_count = 0
        failure_count = 0
        
        for patch in patches:
            if self.applier.apply_patch(patch):
                success_count += 1
            else:
                failure_count += 1
                
        # Return the wrapper object instead of injecting into metadata
        return {
            "original_document": self.raw_document,
            "corrected_document": self.applier.corrected_document,
            "diff_report": self.applier.diff_report,
            "validation_report": None, # To be populated by Orchestrator
            "llm_statistics": {
                "patches_applied": success_count,
                "patches_rejected": failure_count,
                "confidence_in_corrections": response_dict.get("confidence_in_corrections", 0.0)
            },
            "processing_time": 0.0 # To be populated by Orchestrator
        }
