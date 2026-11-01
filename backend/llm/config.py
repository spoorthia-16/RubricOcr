import os
from dotenv import load_dotenv

# Ensure environment variables are loaded from backend/.env
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_file = os.path.join(base_dir, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)
load_dotenv()

# Azure OpenAI API Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# Backward Compatibility Aliases
LLM_MODEL = AZURE_OPENAI_DEPLOYMENT
OPENAI_API_KEY = AZURE_OPENAI_API_KEY

# Pipeline Feature Control Switch
ENABLE_LLM_CORRECTION = os.getenv("ENABLE_LLM_CORRECTION", "True").lower() in ("true", "1", "t")

# Model Execution Hyperparameters
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
TOP_P = float(os.getenv("TOP_P", "0.95"))

# Confidence Thresholds
CONFIDENCE_THRESHOLD_KEEP_AS_IS = 0.98
CONFIDENCE_THRESHOLD_FORCE_REVIEW = 0.85
