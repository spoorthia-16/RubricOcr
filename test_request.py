import requests
import os

url = "http://127.0.0.1:5000/upload"
filepath = "backend/uploads/Rubrics Sample File.pdf"
if not os.path.exists(filepath):
    print("File not found.")
else:
    with open(filepath, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
        print("Status code:", response.status_code)
        print("Response:", response.text)
