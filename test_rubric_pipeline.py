import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.pipeline_orchestrator import process_document

def main():
    image_path = os.path.join(os.path.dirname(__file__), "debug", "table_crop_p1_1.png")
    
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found.")
        return

    print(f"Testing full pipeline on rubric image: {image_path}")
    result = process_document(image_path)
    
    print("\n========== PIPELINE RESULT ==========")
    print(json.dumps(result, indent=4))
    print("=====================================\n")

if __name__ == "__main__":
    main()
