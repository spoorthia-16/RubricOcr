import sys, os, json
sys.path.append(os.path.abspath('backend'))
from services.excel_service import cluster_coords
import openpyxl

# Let's extract X coordinates directly from the ocr_service!
from services.ocr_service import extract_text
data = extract_text('backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf')
x_list = [c['x'] for c in data]
xb = cluster_coords(x_list, 20)
print('X Boundaries:', xb)

# Print cell X values and what column they map to
for c in data:
    if c['text'] in ['Learner name', '1', '2', '3']:
        col_idx = 1
        min_x = float('inf')
        for i, x in enumerate(xb):
            dist = abs(c['x'] - x)
            if dist < min_x:
                min_x = dist
                col_idx = i+1
        print(f"Text: '{c['text']}', w: {c['w']}, x: {c['x']}, mapped to col: {col_idx}")
