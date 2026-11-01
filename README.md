# Rubric OCR

Rubric OCR is an AI-powered system designed to process, parse, and structure tabular assessment rubrics from scanned PDFs and images into standardized spreadsheets using PaddleOCR and Azure OpenAI LLM post-processing.

## Project Structure

```text
RubricOcr/
├── backend/            # Flask backend service (OCR, LLM correction, Excel export)
│   ├── config/         # Layout & style configurations
│   ├── llm/            # Azure OpenAI integration & correction service
│   ├── models/         # Schema and dataclass models
│   ├── routes/         # API routes (upload, process, export)
│   ├── services/       # OCR pipeline, table detection, and excel writer
│   ├── utils/          # Image processing & helper utilities
│   ├── .env.example    # Environment variable template
│   └── app.py          # Backend entry point
├── frontend/           # React + Vite + Tailwind CSS frontend
│   ├── src/            # UI components, pages, and API clients
│   └── package.json
└── README.md
```

## Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables:
   Copy `.env.example` to `.env` and populate your credentials:
   ```bash
   cp .env.example .env
   ```
5. Run the Flask backend:
   ```bash
   python app.py
   ```
   The backend API will be available at `http://127.0.0.1:5001`.

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The application UI will run at `http://localhost:5173`.
