import os
import json
import traceback
from dataclasses import asdict
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from services.pipeline_orchestrator import process_document

upload_bp = Blueprint("upload", __name__)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@upload_bp.route("/upload", methods=["POST"])
def upload_file():

    # Check if file exists
    if "file" not in request.files:
        return jsonify({
            "success": False,
            "message": "No file uploaded"
        }), 400

    file = request.files["file"]

    # Check if filename is empty
    if file.filename == "":
        return jsonify({
            "success": False,
            "message": "No selected file"
        }), 400

    # Validate extension
    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "message": "Unsupported file type"
        }), 400

    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Secure filename
    filename = secure_filename(file.filename)

    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Save uploaded file
    file.save(filepath)

    current_stage = "Initialization"
    
    try:
        print("Running Pipeline Orchestrator...")
        
        result = process_document(filepath)
        
        if result.get("status") != "SUCCESS":
            try:
                with open(os.path.join(os.path.dirname(__file__), "..", "error_log.txt"), "w") as f:
                    f.write(f"Pipeline Failed at Stage: {result.get('failed_stage')}\nReason: {result.get('reason')}")
            except:
                pass
            return jsonify({
                "success": False,
                "status": "failed",
                "stage": result.get("failed_stage", "UNKNOWN"),
                "reason": result.get("reason", "Unknown error")
            }), 500
            
        excel_path = result["excel_file"]
        excel_filename = os.path.basename(excel_path)
        
        # Build grid_data for frontend preview from serialized_document.json
        base_dir = os.path.abspath(os.path.dirname(__file__))
        serialized_path = os.path.join(base_dir, "..", "debug", "serialized_document.json")
        
        grid_data = []
        if os.path.exists(serialized_path):
            with open(serialized_path, "r") as f:
                serialized = json.load(f)
                
            worksheets = serialized.get("workbook", {}).get("worksheets", [])
            if worksheets:
                # We'll just show the first worksheet for preview
                ws = worksheets[0]
                for row in ws.get("rows", []):
                    row_data = []
                    for cell in row.get("cells", []):
                        row_data.append({
                            "value": cell.get("value", ""),
                            "colSpan": cell.get("colspan", 1),
                            "rowSpan": cell.get("rowspan", 1)
                        })
                    grid_data.append(row_data)

        print("Completed.")

        return jsonify({
            "success": True,
            "excel_url": f"http://127.0.0.1:5001/download/{excel_filename}",
            "grid_data": grid_data
        })

    except Exception as e:
        traceback.print_exc()
        
        # Write exact error to a file so we can diagnose
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", "error_log.txt"), "w") as f:
                f.write(traceback.format_exc())
        except:
            pass

        return jsonify({
            "success": False,
            "status": "failed",
            "stage": current_stage,
            "reason": str(e)
        }), 500

@upload_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        output_folder = os.path.join(base_dir, "..", "exports")
        excel_path = os.path.join(output_folder, secure_filename(filename))
        
        if not os.path.exists(excel_path):
            return jsonify({"success": False, "message": "File not found"}), 404
            
        return send_file(
            excel_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@upload_bp.route("/dashboard", methods=["GET"])
def get_dashboard_data():
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        output_folder = os.path.join(base_dir, "..", "exports")
        
        files = []
        if os.path.exists(output_folder):
            for filename in os.listdir(output_folder):
                if filename.endswith(".xlsx"):
                    filepath = os.path.join(output_folder, filename)
                    stat = os.stat(filepath)
                    files.append({
                        "filename": filename,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "size": stat.st_size,
                        "url": f"http://127.0.0.1:5001/download/{filename}"
                    })
                    
        # Sort files by newest first
        files.sort(key=lambda x: x["created_at"], reverse=True)
                    
        return jsonify({
            "success": True,
            "total_processed": len(files),
            "files": files
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@upload_bp.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        output_folder = os.path.join(base_dir, "..", "exports")
        file_path = os.path.join(output_folder, secure_filename(filename))
        
        if os.path.exists(file_path) and file_path.startswith(output_folder):
            os.remove(file_path)
            return jsonify({"success": True, "message": "File deleted successfully"})
        else:
            return jsonify({"success": False, "message": "File not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500