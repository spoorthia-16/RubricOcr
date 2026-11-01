import sys
import os

sys.path.append(os.path.abspath('backend'))
from services.ocr_service import extract_text
from services.excel_service import generate_excel

filepath = 'backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf'
cell_data = extract_text(filepath)
generate_excel(cell_data, "test_absolute_grid.xlsx")
print("Done!")
