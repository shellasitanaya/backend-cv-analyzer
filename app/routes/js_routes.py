# filename: js_routes.py
# location: backend-cv-analyzer/app/routes/

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

# --- Impor dari bagian Analisis & Scoring (Ferrel) ---
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import calculate_match_score, check_ats_friendliness, analyze_keywords

# --- Impor dari bagian Generate CV & Phrasing (Tugas Anda) ---
from app.services.openai_service import get_phrasing_suggestion
from app.services.cv_generator import build_cv
import app.database as db_service

# Membuat blueprint tunggal untuk semua fitur Job Seeker
# Prefix /api/jobseeker akan digunakan untuk semua rute di file ini
js_bp = Blueprint('jobseeker_api', __name__, url_prefix='/api/jobseeker')

# Folder sementara untuk menyimpan CV yang diunggah
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =================================================================
# ENDPOINT UNTUK ANALISIS CV (DARI FERREL)
# Deskripsi: Menerima upload file CV dan deskripsi pekerjaan, lalu mengembalikan analisis lengkap.
# =================================================================
@js_bp.route('/analyze', methods=['POST'])
def analyze_cv():
    """
    Endpoint untuk menganalisis CV yang diunggah terhadap deskripsi pekerjaan.
    """
    # 1. Validasi Input
    if 'cv_file' not in request.files:
        return jsonify({"error": "File CV (cv_file) tidak ditemukan"}), 400

    cv_file = request.files['cv_file']
    job_description = request.form.get('job_description', '')

    if cv_file.filename == '' or not job_description:
        return jsonify({"error": "File CV dan deskripsi pekerjaan tidak boleh kosong"}), 400

    # 2. Proses File
    filename = secure_filename(cv_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        cv_file.save(file_path)

        # 3. Ekstrak Teks dari CV
        cv_text = extract_text(file_path)
        if not cv_text:
            raise ValueError("Teks tidak dapat diekstrak dari file CV.")

        # 4. Panggil semua fungsi analisis dari ai_analyzer.py
        score = calculate_match_score(cv_text, job_description)
        ats_results = check_ats_friendliness(cv_text)
        keyword_results = analyze_keywords(cv_text, job_description)

        # 5. Gabungkan semua hasil menjadi satu respons JSON
        analysis_result = {
            "match_score": score,
            "ats_friendliness": ats_results,
            "keyword_analysis": keyword_results,
            "message": "Analisis berhasil."
        }
        
        # Di sini bisa ditambahkan logika untuk menyimpan hasil analisis ke tabel `Analyses`
        # contoh: db_service.save_analysis(user_id, analysis_result)

        return jsonify(analysis_result), 200

    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500
    finally:
        # 6. Hapus file sementara setelah selesai
        if os.path.exists(file_path):
            os.remove(file_path)

# =================================================================
# ENDPOINT UNTUK AI PHRASING (TUGAS ANDA)
# Deskripsi: Menerima sepotong teks dan mengembalikannya dalam versi yang lebih baik.
# =================================================================
@js_bp.route('/suggest-phrasing', methods=['POST'])
def suggest_phrasing_endpoint():
    """
    Endpoint untuk menerima teks dan mengembalikan saran perbaikan dari AI.
    """
    data = request.get_json()
    
    if not data or 'text_input' not in data:
        return jsonify({"error": "Request body harus berisi 'text_input'"}), 400
    
    text_input = data.get('text_input')
    context = data.get('context', 'work_experience')

    try:
        suggested_text = get_phrasing_suggestion(text_input, context)
        return jsonify({"suggested_text": suggested_text})
    except Exception as e:
        return jsonify({"error": "Gagal memproses permintaan AI", "details": str(e)}), 500

# =================================================================
# ENDPOINT UNTUK GENERATE CV (TUGAS ANDA)
# Deskripsi: Menerima data CV lengkap dalam format JSON dan menghasilkan file PDF.
# =================================================================
@js_bp.route('/generate-cv', methods=['POST'])
def generate_cv_endpoint():
    """
    Endpoint untuk menerima data CV lengkap dan men-generate file PDF.
    """
    data = request.get_json()

    # 1. Validasi input JSON dari frontend
    required_fields = ['original_cv_id', 'template_name', 'cv_data', 'user_id']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Request body tidak lengkap. Membutuhkan: " + ", ".join(required_fields)}), 400

    template_name = data.get('template_name')
    cv_data = data.get('cv_data')
    original_cv_id = data.get('original_cv_id')

    # 2. Panggil service untuk membuat file PDF
    pdf_relative_path = create_cv_pdf(template_name, cv_data)
    
    if not pdf_relative_path:
        return jsonify({"error": "Gagal membuat file PDF."}), 500

    # 3. Simpan catatan ke database untuk versioning
    try:
        last_version = db_service.get_last_cv_version(original_cv_id)
        new_version_number = (last_version or 0) + 1

        generated_cv_info = {
            'template_name': template_name,
            'version_number': new_version_number,
            'storage_path': pdf_relative_path 
        }

        generated_cv_id = db_service.save_generated_cv(original_cv_id, generated_cv_info)

    except Exception as e:
        # Jika PDF berhasil dibuat tapi gagal simpan ke DB, tetap berikan link unduhan
        return jsonify({
            "message": "PDF created but failed to save version history.",
            "download_url": pdf_relative_path,
            "error": str(e)
        }), 500

    # 4. Kirim respons sukses jika semuanya berjalan lancar
    return jsonify({
        "message": "CV generated successfully!",
        "download_url": pdf_relative_path,
        "generated_cv_id": generated_cv_id,
        "version": new_version_number
    }), 201