import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TEMP_FOLDER = os.path.join(BASE_DIR, "temp")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")

POPPLER_PATH = r"C:\Users\spoor\OneDrive\Desktop\Release-26.02.0-0\poppler-26.02.0\Library\bin"
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# OCR Routing Thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.80

# GPT Review & LLM Correction Engine Orchestration
GPT_BATCH_SIZE = 10
GPT_MAX_RETRIES = 3
GPT_TIMEOUT = 60
ENABLE_LLM_CORRECTION = os.getenv("ENABLE_LLM_CORRECTION", "True").lower() in ("true", "1", "t")
DEBUG_PIPELINE = os.getenv("DEBUG_PIPELINE", "True").lower() in ("true", "1", "t")

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


