import json

with open('c:/Users/spoor/EXCEL works/Project1/backend/debug/DOC_5/09_cell_mapping.json', encoding='utf-8') as f:
    mapping = json.load(f)['cell_mapping']

def print_row(row_idx, label):
    print(f'--- {label} ---')
    for cell in mapping:
        if cell['row'] == row_idx and cell['mapped_text'].strip():
            text = cell['mapped_text'].encode('utf-8', 'replace').decode('utf-8')
            print(f"Col {cell['column']} : {text}")

print_row(8, "Headers Row")
print_row(9, "Learner 1 Row")
print_row(23, "Learner 15 Row")
print_row(24, "Learner 16 Row")
