from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any, Optional

class TableRow(BaseModel):
    """Represents a single row in a table. We use a generic dict to allow flexible column names."""
    cells: Dict[str, str] = Field(..., description="Dictionary mapping column headers to cell text")

class Table(BaseModel):
    """Represents an individual table within the document."""
    headers: List[str] = Field(..., description="List of column headers")
    rows: List[Dict[str, str]] = Field(..., description="List of rows, where each row is a dictionary of header-to-value mappings")
    title: Optional[str] = Field(None, description="Optional title or description of the table")

class DocumentSchema(BaseModel):
    """The root schema for the entire reconstructed document."""
    document_type: str = Field(..., description="The classification of the document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Any key-value metadata extracted outside the tables (e.g., Learner Name, Date)")
    tables: List[Table] = Field(..., description="The list of tables extracted from the image")

def validate_document(json_data: dict) -> dict:
    """
    Validates the raw JSON output from the LLM against the strict Pydantic schema.
    If the JSON is malformed or missing required structures (like tables/rows), 
    it raises a ValidationError and prevents Excel generation.
    """
    # This will raise a ValidationError if the json_data doesn't match the schema perfectly
    validated_model = DocumentSchema(**json_data)
    
    # Return the clean, validated dictionary
    return validated_model.model_dump()
