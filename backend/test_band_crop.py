import os
import json

doc_dir = "c:/Users/spoor/EXCEL works/Project1/backend/debug/DOC_1"
matrix_path = os.path.join(doc_dir, "06_table_matrix.json")

with open(matrix_path, 'r') as f:
    data = json.load(f)

matrix = data['tables'][0]['matrix']

tall_cells = []
for r in range(min(4, len(matrix))):
    for cell in matrix[r]:
        w = cell['width']
        h = cell['height']
        if h > w * 1.2:
            tall_cells.append(cell)

for i, c in enumerate(tall_cells):
    print(f"Cell {i}: row={c.get('row')}, col={c.get('column')}, w={c.get('width')}, h={c.get('height')}, bbox={c.get('bbox')}")
