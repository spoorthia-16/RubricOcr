from pydantic import BaseModel
from typing import List, Optional

class CellPatch(BaseModel):
    table_index: int
    row_index: int
    column_index: int
    old_value: str
    new_value: str
    reason: str

class CorrectionResponse(BaseModel):
    """
    The structured response expected from the LLM. 
    It returns a list of patches rather than rewriting the entire document, 
    preventing structural hallucinations.
    """
    patches: List[CellPatch]
    confidence_in_corrections: float
    notes: Optional[str] = None
