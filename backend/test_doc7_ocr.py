import os
import sys

# Ensure backend is in path
sys.path.append('c:/Users/spoor/EXCEL works/Project1/backend')
from services.ocr_service import extract_text

pdf_path = "c:/Users/spoor/EXCEL works/Project1/backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf"
output_dir = "c:/Users/spoor/EXCEL works/Project1/backend/debug/test_ocr"
os.makedirs(output_dir, exist_ok=True)

print("Running OCR on DOC_7...")
result = extract_text(pdf_path)
print("Finished!")
import json
with open(os.path.join(output_dir, "test_result.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
