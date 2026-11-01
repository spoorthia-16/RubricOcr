import sys
import os

sys.path.append(os.path.abspath('backend'))
from services.ocr_service import extract_text

# Use a test file that exists in the backend or uploads folder
# Assuming there is a file in uploads folder
uploads_dir = 'backend/uploads'
if os.path.exists(uploads_dir):
    files = os.listdir(uploads_dir)
    if files:
        filepath = os.path.join(uploads_dir, files[-1])
        print(f"Testing with file: {filepath}")
        try:
            res = extract_text(filepath)
            print("Extraction successful.")
        except Exception as e:
            import traceback
            traceback.print_exc()
    else:
        print("No files in uploads dir.")
else:
    print("Uploads dir does not exist.")
