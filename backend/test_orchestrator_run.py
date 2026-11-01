import os
import sys

# Add backend directory to PYTHONPATH
base_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.append(base_dir)

from services.pipeline_orchestrator import process_document

test_file = os.path.join(base_dir, "temp", "processed_test.png")
if not os.path.exists(test_file):
    print(f"Test file not found: {test_file}")
    sys.exit(1)

result = process_document(test_file)
print(result)
