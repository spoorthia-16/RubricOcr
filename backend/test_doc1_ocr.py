import os
import sys
import json
sys.path.append('c:/Users/spoor/EXCEL works/Project1/backend')
from services.ocr_service import extract_text

pdf_path = "c:/Users/spoor/EXCEL works/Project1/backend/uploads/DOC_1.pdf"
output_dir = "c:/Users/spoor/EXCEL works/Project1/backend/debug/test_ocr"
os.makedirs(output_dir, exist_ok=True)

print(f"Running OCR on {pdf_path}...")
result = extract_text(pdf_path)
print("Finished extract_text!")

val_file = os.path.join(os.path.dirname(result["page_image"]), "14_header_validation.json")
if os.path.exists(val_file):
    print("\n--- Header Validation Output ---")
    with open(val_file, 'r', encoding='utf-8') as f:
        print(f.read())
else:
    print("\nNo 14_header_validation.json found!")
