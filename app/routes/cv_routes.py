from flask import Blueprint, jsonify, send_file, request
from app.services.cv_generator import build_cv
from app.models import Candidate
import os
from PIL import Image
import pytesseract

cv_bp = Blueprint("cv", __name__)

# === [1] Upload CV Gambar untuk OCR ===
@cv_bp.route("/upload_cv", methods=["POST"])
def upload_cv():
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
@cv_bp.route("/api/cv/generate/<candidate_id>", methods=["GET"])
def generate_cv(candidate_id):
    print(f"🔍 Candidate ID recieved: {candidate_id}")

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
