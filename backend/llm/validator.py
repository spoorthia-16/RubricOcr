import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("LLMClient")


class Validator:
    """
    4-Level Validation Engine for LLM Execution Pipeline.
    
    Level 1: Transport Validation (Empty response, Timeout, Rate limit, JSON parse error)
    Level 2: Schema Validation (Matches CorrectionResponse schema)
    Level 3: Patch Validation (Existing path, legal operation, correct datatype)
    Level 4: Business Validation (Header typos allowed, Marks/Numeric changes rejected unless explicitly allowed)
    """

    def __init__(self, allow_numeric_corrections: bool = False):
        self.allow_numeric_corrections = allow_numeric_corrections

    def validate_transport(
        self, raw_response: Optional[str], transport_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Level 1: Transport Validation
        Did GPT return anything? Timeout? Rate limit? JSON parse error?
        """
        if transport_meta is None:
            transport_meta = {}

        if transport_meta.get("timeout"):
            logger.error("VALIDATION_FAILED: Level 1 - Transport Timeout")
            return {
                "status": "error",
                "level": "Level 1: Transport",
                "reason": "LLM API request timed out",
            }

        if transport_meta.get("rate_limit"):
            logger.error("VALIDATION_FAILED: Level 1 - Rate Limit Exceeded")
            return {
                "status": "error",
                "level": "Level 1: Transport",
                "reason": "LLM API rate limit exceeded",
            }

        if not raw_response or not raw_response.strip():
            logger.error("VALIDATION_FAILED: Level 1 - Empty response from LLM")
            return {
                "status": "error",
                "level": "Level 1: Transport",
                "reason": "Empty response received from LLM",
            }

        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_response = "\n".join(lines).strip()

        try:
            data = json.loads(clean_response)
            return {"status": "success", "data": data, "level": "Level 1: Transport"}
        except json.JSONDecodeError as e:
            logger.error(f"VALIDATION_FAILED: Level 1 - JSON Parse error: {str(e)}")
            return {
                "status": "error",
                "level": "Level 1: Transport",
                "reason": f"JSON parse error: {str(e)}",
            }


    def _parse_patch_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parses individual patch dictionary into normalized schema format."""
        if not isinstance(item, dict):
            return None

        # Standard key format
        if "table_index" in item and "row_index" in item and "column_index" in item:
            try:
                return {
                    "table_index": int(item["table_index"]),
                    "row_index": int(item["row_index"]),
                    "column_index": int(item["column_index"]),
                    "old_value": item.get("old_value", ""),
                    "new_value": item.get("new_value", item.get("value", "")),
                    "reason": item.get("reason", "LLM correction"),
                    "op": item.get("op", "replace"),
                }
            except (ValueError, TypeError):
                return None

        # JSON-Patch / RFC 6902 path syntax (/tables/0/rows/0/cells/0/text)
        path_str = str(item.get("path", ""))
        if path_str:
            import re
            match = re.search(r'/tables/(\d+)/rows/(\d+)/cells/(\d+)', path_str)
            if match:
                t_idx, r_idx, c_idx = map(int, match.groups())
                return {
                    "table_index": t_idx,
                    "row_index": r_idx,
                    "column_index": c_idx,
                    "old_value": item.get("old_value", ""),
                    "new_value": item.get("new_value", item.get("value", "")),
                    "reason": item.get("reason", "LLM JSON-Patch correction"),
                    "op": item.get("op", "replace"),
                }
        return None

    def validate_schema(self, data: Any) -> Dict[str, Any]:
        """
        Level 2: Schema Validation
        Validates payload against CorrectionResponse schema or JSON-Patch list format.
        Normalizes patches into uniform schema objects.
        """
        patches = []

        if isinstance(data, list):
            for item in data:
                parsed = self._parse_patch_item(item)
                if parsed:
                    patches.append(parsed)
            return {"status": "success", "data": {"patches": patches}, "level": "Level 2: Schema"}

        if isinstance(data, dict):
            if "patches" not in data or not isinstance(data["patches"], list):
                logger.error("VALIDATION_FAILED: Level 2 - Missing or invalid 'patches' key")
                return {
                    "status": "error",
                    "level": "Level 2: Schema",
                    "reason": "Missing or invalid 'patches' list in response payload",
                }

            raw_patches = data.get("patches", [])
            for item in raw_patches:
                parsed = self._parse_patch_item(item)
                if parsed:
                    patches.append(parsed)
            return {"status": "success", "data": {"patches": patches}, "level": "Level 2: Schema"}


        logger.error("VALIDATION_FAILED: Level 2 - Root payload is not an object or array")
        return {
            "status": "error",
            "level": "Level 2: Schema",
            "reason": "Root response object must be a dictionary or list of patches",
        }


    def validate_patch(
        self, patch: Dict[str, Any], raw_document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Level 3: Patch Validation
        Every patch must satisfy:
        - existing path (valid table, row, column indices)
        - legal operation
        - correct datatype
        """
        required_keys = ["table_index", "row_index", "column_index", "new_value"]
        for key in required_keys:
            if key not in patch:
                return {
                    "status": "error",
                    "level": "Level 3: Patch",
                    "reason": f"Missing required patch attribute '{key}'",
                }

        # 1. Correct datatype validation
        t_idx = patch.get("table_index")
        r_idx = patch.get("row_index")
        c_idx = patch.get("column_index")
        new_val = patch.get("new_value")

        if not isinstance(t_idx, int) or isinstance(t_idx, bool):
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"table_index must be an integer, got {type(t_idx).__name__}",
            }
        if not isinstance(r_idx, int) or isinstance(r_idx, bool):
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"row_index must be an integer, got {type(r_idx).__name__}",
            }
        if not isinstance(c_idx, int) or isinstance(c_idx, bool):
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"column_index must be an integer, got {type(c_idx).__name__}",
            }
        if isinstance(new_val, (dict, list)):
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": "new_value must be a primitive scalar, cannot be nested object or array",
            }

        # 2. Legal operation check
        op = patch.get("op", "replace")
        if op not in ("replace", "update", "correct"):
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"Illegal patch operation '{op}'",
            }

        # 3. Existing path validation
        tables = raw_document.get("tables", [])
        if not isinstance(tables, list) or not (0 <= t_idx < len(tables)):
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"Table index {t_idx} out of bounds (document has {len(tables)} tables)",
            }

        table = tables[t_idx]
        rows = table.get("rows", [])
        target_row = next((r for r in rows if r.get("index") == r_idx), None)
        if not target_row:
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"Row index {r_idx} does not exist in table {t_idx}",
            }

        target_cell = next(
            (c for c in target_row.get("cells", []) if c.get("column") == c_idx), None
        )
        if not target_cell:
            return {
                "status": "error",
                "level": "Level 3: Patch",
                "reason": f"Column index {c_idx} does not exist in table {t_idx}, row {r_idx}",
            }

        return {"status": "success", "level": "Level 3: Patch", "target_cell": target_cell}

    def validate_business_rules(
        self,
        patch: Dict[str, Any],
        old_value: Any,
        allow_override: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Level 4: Business Validation
        Header spelling fixes (e.g. Appcarance -> Appearance): Allowed.
        Marks / Numeric alterations (e.g. 4 -> 9): Rejected unless business rules explicitly allow such corrections.
        """
        permit_numeric = (
            allow_override
            if allow_override is not None
            else self.allow_numeric_corrections
        )
        new_val_str = str(patch.get("new_value", "")).strip()
        old_val_str = str(old_value if old_value is not None else "").strip()

        # Check if both values represent numbers (e.g., marks, scores, quantities)
        def is_numeric(val: str) -> bool:
            if not val:
                return False
            try:
                float(val.replace(",", ""))
                return True
            except ValueError:
                return False

        if is_numeric(old_val_str) and is_numeric(new_val_str):
            old_num = float(old_val_str.replace(",", ""))
            new_num = float(new_val_str.replace(",", ""))
            if old_num != new_num and not permit_numeric:
                return {
                    "status": "error",
                    "level": "Level 4: Business",
                    "reason": f"Numeric marks alteration rejected: '{old_val_str}' -> '{new_val_str}' is forbidden by business rules",
                }

        return {"status": "success", "level": "Level 4: Business"}
