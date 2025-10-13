from flask import Blueprint, jsonify, send_file, request, current_app
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

# === [3] Generate CV dari input manual ===
@cv_bp.route("/api/cv/generate_custom", methods=["POST"])
def generate_custom_cv():
    data = request.get_json()
    template_name = data.get("template", "modern")

    try:
        # Simpan data sementara
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import HTML
        import tempfile

        template_dir = os.path.join(current_app.root_path, "template")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(f"{template_name}.html")

        rendered_html = template.render(data=data)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            HTML(string=rendered_html).write_pdf(tmp_pdf.name)
            return send_file(tmp_pdf.name, as_attachment=True, download_name="generated_cv.pdf")

    except Exception as e:
        print(f"❌ Error generating CV: {e}")
        return jsonify({"error": str(e)}), 500

@cv_bp.route("/api/cv/preview", methods=["POST"])
def preview_cv():
    """
    Generate CV PDF langsung dari data yang dikirim user (tanpa database)
    """
    from app.services.cv_generator import build_cv_from_data
    from flask import send_file, jsonify, request

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        template = data.get("template", "modern")
        output_path = build_cv_from_data(data, template)
        return send_file(output_path, mimetype="application/pdf", as_attachment=False)

    except Exception as e:
        print(f"❌ Error generating CV preview: {e}")
        return jsonify({"error": str(e)}), 500

