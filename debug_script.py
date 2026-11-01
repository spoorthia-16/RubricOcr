import json

with open('debug/paddle_raw_output.json') as f:
    data = json.load(f)

for b in data:
    if 'Learner' in b['text'] or 'Learner_002' in b['text']:
        print(f"{b['text']}: {b['box']}")
