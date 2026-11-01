import sys
import os

sys.path.append(os.path.abspath('backend'))
from services.ocr_service import extract_text
from services.excel_service import generate_excel

uploads_dir = 'backend/uploads'
if os.path.exists(uploads_dir):
    files = os.listdir(uploads_dir)
    if files:
        filepath = os.path.join(uploads_dir, files[-1])
        print(f"Testing with file: {filepath}")
        try:
            res = extract_text(filepath)
            print("Extraction successful.")
            generate_excel(res, 'test_output.xlsx')
            print("Excel generation successful.")
        except Exception as e:
            import traceback
            traceback.print_exc()
    else:
        print("No files in uploads dir.")
else:
    print("Uploads dir does not exist.")
