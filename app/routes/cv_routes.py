from flask import Blueprint, send_file, request, current_app, jsonify
from app.services.cv_generator import build_cv, build_cv_from_data
from app.models import Candidate
import os
from PIL import Image
import pytesseract

cv_bp = Blueprint("cv", __name__)

# === [1] Upload CV Gambar untuk OCR ===
@cv_bp.route("/upload_cv", methods=["POST", "OPTIONS"])
def upload_cv():
    if request.method == "OPTIONS":
        return jsonify({"status": "success"}), 200
        
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    upload_folder = "uploads"
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, file.filename)
    file.save(filepath)

    try:
        text = pytesseract.image_to_string(Image.open(filepath))
        os.remove(filepath)
        return jsonify({"message": "CV extracted successfully", "extracted_text": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === [2] Generate CV PDF dari tabel Candidate ===
@cv_bp.route("/generate/<candidate_id>", methods=["GET", "OPTIONS"])
def generate_cv(candidate_id):
    if request.method == "OPTIONS":
        return jsonify({"status": "success"}), 200
        
    print(f"🔍 Candidate ID received: {candidate_id}")

    candidate = Candidate.query.filter_by(id=candidate_id).first()
    if not candidate:
        return jsonify({"error": f"Candidate with the ID {candidate_id} is not found"}), 404

    try:
        output_path = build_cv(candidate_id)
        abs_path = os.path.abspath(output_path)
        print(f"✅ Sending file: {abs_path}")
        return send_file(abs_path, as_attachment=True)

    except Exception as e:
        print(f"❌ Failed to generate CV: {e}")
        return jsonify({"error": f"Failed to generate CV: {e}"}), 500

# === [3] Generate CV dari input manual ===
@cv_bp.route("/generate_custom", methods=["POST", "OPTIONS"])
def generate_custom_cv():
    if request.method == "OPTIONS":
        return jsonify({"status": "success"}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        print("🔍 [GENERATE_CUSTOM] Received request")
        template_name = data.get("template", "modern")

        # Use build_cv_from_data instead of manual template rendering
        from app.services.cv_generator import build_cv_from_data
        
        output_path = build_cv_from_data(data, template_name)
        return send_file(output_path, as_attachment=True, download_name="generated_cv.pdf")

    except Exception as e:
        print(f"❌ [GENERATE_CUSTOM] Error: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ [GENERATE_CUSTOM] Traceback:\n{error_details}")
        
        return jsonify({
            "error": "Failed to generate CV",
            "details": str(e),
            "type": type(e).__name__
        }), 500
    
# === [4] Preview CV (endpoint yang digunakan frontend) ===
@cv_bp.route("/preview", methods=["POST", "OPTIONS"])
def preview_cv():
    """
    Generate CV PDF langsung dari data yang dikirim user (tanpa database)
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "success"}), 200
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        print("🔍 [ROUTE] Received CV generation request")
        template = data.get("template", "modern")
        
        output_path = build_cv_from_data(data, template)
        return send_file(output_path, mimetype="application/pdf", as_attachment=False)

    except FileNotFoundError as e:
        print(f"❌ [ROUTE] Template not found: {e}")
        return jsonify({"error": f"Template not found: {str(e)}"}), 404
    except Exception as e:
        print(f"❌ [ROUTE] Error generating CV preview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate CV: {str(e)}"}), 500