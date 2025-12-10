import base64
from flask import Blueprint, send_file, request, current_app, jsonify, session
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

@cv_bp.route('generate_custom', methods=['POST'])
def generate_custom_cv():
    try:
        data = request.json
        print("📥 Received CV generation request")
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        # Extract parameters
        template = data.get('template', 'ats-friendly')
        use_ai_phrasing = data.get('use_ai_phrasing', True)
        
        print(f"🔧 Template: {template}, AI Phrasing: {use_ai_phrasing}")
        
        # Generate CV
        pdf_path, processed_data = build_cv_from_data(
            data, 
            template=template, 
            use_ai_phrasing=use_ai_phrasing
        )
        
        # Read PDF file and convert to base64
        with open(pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Clean up temp file
        try:
            os.remove(pdf_path)
        except:
            pass
        
        print("✅ CV generated successfully")
        
        return jsonify({
            "success": True,
            "pdf_base64": pdf_base64,
            "processed_data": processed_data,
            "message": "CV generated with proper bullet point formatting"
        })
        
    except Exception as e:
        print(f"❌ Error generating CV: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate CV"
        }), 500

@cv_bp.route("/get_last_cv_data", methods=["GET"])
def get_last_cv_data():
    """
    Get the last generated CV data for editing
    """
    last_data = session.get('last_cv_data')
    last_template = session.get('last_template', 'modern')
    
    if last_data:
        return jsonify({
            'success': True,
            'data': last_data,
            'template': last_template
        })
    else:
        return jsonify({
            'success': False,
            'error': 'No previous CV data found'
        }), 404
    
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
        use_ai_phrasing = data.get("use_ai_phrasing", True)  # Default true
        
        output_path = build_cv_from_data(data, template, use_ai_phrasing)
        return send_file(output_path, mimetype="application/pdf", as_attachment=False)

    except FileNotFoundError as e:
        print(f"❌ [ROUTE] Template not found: {e}")
        return jsonify({"error": f"Template not found: {str(e)}"}), 404
    except Exception as e:
        print(f"❌ [ROUTE] Error generating CV preview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate CV: {str(e)}"}), 500