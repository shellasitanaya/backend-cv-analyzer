from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
# scoring and analysis imports
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import calculate_match_score, check_ats_friendliness, analyze_keywords

# --- Impor dari bagian Generate CV & Phrasing (Tugas Anda) ---
# from app.services.openai_service import get_phrasing_suggestion
from app.services.cv_generator import build_cv

# Prefix /api/jobseeker akan digunakan untuk semua rute di file ini
js_bp = Blueprint('jobseeker_api', __name__, url_prefix='/api/jobseeker')

# Folder sementara untuk menyimpan CV yang diunggah
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =================================================================
# ENDPOINT UNTUK ANALISIS CV (FERREL)
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
# ENDPOINT UNTUK AI PHRASING (TOTO) - DIPAKAI NANTI (masih cari model)
# Deskripsi: Menerima sepotong teks dan mengembalikannya dalam versi yang lebih baik.
# =================================================================
# @js_bp.route('/suggest-phrasing', methods=['POST'])
# def suggest_phrasing_endpoint():
#     """
#     Endpoint untuk menerima teks dan mengembalikan saran perbaikan dari AI.
#     """
#     data = request.get_json()
    
#     if not data or 'text_input' not in data:
#         return jsonify({"error": "Request body harus berisi 'text_input'"}), 400
    
#     text_input = data.get('text_input')
#     context = data.get('context', 'work_experience')

#     try:
#         suggested_text = get_phrasing_suggestion(text_input, context)
#         return jsonify({"suggested_text": suggested_text})
#     except Exception as e:
#         return jsonify({"error": "Gagal memproses permintaan AI", "details": str(e)}), 500