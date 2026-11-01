import re
from typing import Dict, Any

def normalize_text(text: str) -> str:
    """Normalizes OCR text (e.g., stripping excess spaces and line endings)."""
    if not text:
        return ""
    text = text.strip()
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    return '\n'.join(lines)


class Preprocessor:
    """Transforms raw OCR output into a compact, LLM-friendly payload."""
    
    def __init__(self, raw_document: Dict[str, Any]):
        self.raw_document = raw_document
        self.stats = {
            "total_cells": 0,
            "low_confidence_cells": 0,
            "sum_confidence": 0.0
        }

    def _process_tables(self) -> list:
        compact_tables = []
        
        for t_idx, table in enumerate(self.raw_document.get("tables", [])):
            compact_table = {
                "table_index": t_idx,
                "name": table.get("name", f"Table_{t_idx}"),
                "rows": []
            }
            
            for r_idx, row in enumerate(table.get("rows", [])):
                compact_row = {
                    "row_index": row.get("index", r_idx),
                    "cells": []
                }
                
                for c_idx, cell in enumerate(row.get("cells", [])):
                    raw_text = cell.get("value", "")
                    normalized = normalize_text(raw_text)
                    conf = cell.get("confidence", 1.0)
                    
                    self.stats["total_cells"] += 1
                    self.stats["sum_confidence"] += conf
                    if conf < 0.85:
                        self.stats["low_confidence_cells"] += 1
                        
                    # Skip completely empty structural cells to save tokens
                    if not normalized:
                        continue
                        
                    compact_cell = {
                        "row": cell.get("row", r_idx),
                        "column": cell.get("column", c_idx),
                        "text": normalized,
                        "confidence": round(conf, 3)
                    }
                    
                    if cell.get("rowspan", 1) > 1:
                        compact_cell["rowspan"] = cell["rowspan"]
                    if cell.get("colspan", 1) > 1:
                        compact_cell["colspan"] = cell["colspan"]
                        
                    compact_row["cells"].append(compact_cell)
                    
                if compact_row["cells"]:
                    compact_table["rows"].append(compact_row)
            
            if compact_table["rows"]:
                compact_tables.append(compact_table)
                
        return compact_tables

    def build_payload(self) -> Dict[str, Any]:
        """Generates the final token-efficient JSON payload."""
        payload = {}
        
        if "metadata_regions" in self.raw_document:
            payload["metadata"] = self.raw_document["metadata_regions"]
            
        payload["tables"] = self._process_tables()
        
        # Calculate final stats
        if self.stats["total_cells"] > 0:
            avg_conf = self.stats["sum_confidence"] / self.stats["total_cells"]
        else:
            avg_conf = 1.0
            
        payload["statistics"] = {
            "total_cells": self.stats["total_cells"],
            "low_confidence_cells": self.stats["low_confidence_cells"],
            "average_confidence": round(avg_conf, 3)
        }
        
        return payload
