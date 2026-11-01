import sys
sys.path.append('c:/Users/spoor/EXCEL works/Project1/backend')
from services.pipeline_orchestrator import process_document
import os

pdf_path = "c:/Users/spoor/EXCEL works/Project1/backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf"
try:
    result = process_document(pdf_path)
    print("Pipeline completed successfully.")
except Exception as e:
    print(f"Pipeline failed: {e}")
