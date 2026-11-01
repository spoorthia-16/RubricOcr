from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class OCRCell(BaseModel):
    row: int
    column: int
    value: str
    rowspan: int = 1
    colspan: int = 1
    confidence: float = 1.0

class OCRRow(BaseModel):
    index: int
    cells: List[OCRCell]

class OCRTable(BaseModel):
    name: str
    rows: List[OCRRow]
    dimensions: Optional[Dict[str, int]] = None
    merged_regions: Optional[List[Dict[str, int]]] = None

class Metadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    additional_info: Optional[Dict[str, str]] = None

class OCRDocument(BaseModel):
    document_info: Dict[str, Any]
    metadata_regions: Optional[Dict[str, str]] = None
    tables: List[OCRTable]

class CorrectionResult(BaseModel):
    original_document: Dict[str, Any]
    corrected_document: Dict[str, Any]
    applied_patches: List[Dict[str, Any]] = []
    rejected_patches: List[Dict[str, Any]] = []
    validation_report: Dict[str, Any] = {}
    llm_latency: float = 0.0
    tokens: Dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    model: str = "gpt-4.1"
    retry_count: int = 0
    patch_count: int = 0
    accepted_patch_count: int = 0
    rejected_patch_count: int = 0
    validation_duration: float = 0.0

