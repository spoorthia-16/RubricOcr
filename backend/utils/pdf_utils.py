import os
import PyPDF2
from pdf2image import convert_from_path
from config import POPPLER_PATH
from config.preprocessing_config import PDF_DPI, DEBUG_OUTPUT_DIR

def validate_pdf(file_path):
    """
    Validates a PDF file.
    Returns:
        {
            "valid": bool,
            "pages": int,
            "filename": str,
            "errors": list
        }
    """
    result = {
        "valid": False,
        "pages": 0,
        "filename": os.path.basename(file_path) if file_path else None,
        "errors": []
    }
    
    if not file_path or not os.path.exists(file_path):
        result["errors"].append(f"File does not exist: {file_path}")
        return result
        
    if not file_path.lower().endswith('.pdf'):
        result["errors"].append("File is not a PDF.")
        return result
        
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        result["errors"].append("File is empty.")
        return result
        
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            num_pages = len(reader.pages)
            if num_pages == 0:
                result["errors"].append("PDF has no pages.")
            else:
                result["pages"] = num_pages
                result["valid"] = True
    except Exception as e:
        result["errors"].append(f"PDF is unreadable or corrupted: {str(e)}")
        
    return result

def render_pdf(file_path):
    """
    Renders every page of a PDF at the configured DPI.
    Saves original debug images to DEBUG_OUTPUT_DIR/pages/page_{n}_original.png.
    Returns a list of image objects.
    """
    try:
        images = convert_from_path(file_path, dpi=PDF_DPI, poppler_path=POPPLER_PATH)
    except Exception as e:
        raise Exception(f"Failed to render PDF: {str(e)}")
        
    base_dir = os.path.abspath(os.path.dirname(__file__))
    pages_dir = os.path.join(base_dir, "..", DEBUG_OUTPUT_DIR, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    
    for i, img in enumerate(images, start=1):
        output_path = os.path.join(pages_dir, f"page_{i}_original.png")
        img.save(output_path, "PNG")
        
    return images
