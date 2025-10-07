# File: app/routes/js_routes.py

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

# Import servis yang sudah ada
from app.services.cv_parser import extract_text
from app.services.ai_analyzer import parse_candidate_info, calculate_match_score, check_ats_friendliness, analyze_keywords # Kita akan tambahkan fungsi baru nanti
from app import database # Nanti kita akan pakai ini untuk menyimpan hasil

js_bp = Blueprint('js_api', __name__, url_prefix='/api/js')

# Folder sementara untuk menyimpan CV yang diunggah
UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@js_bp.route('/analyze', methods=['POST'])
def analyze_cv():
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

        # 4. Panggil Servis AI untuk Analisis
        score = calculate_match_score(cv_text, job_description)
        # Anda akan menambahkan pemanggilan fungsi lain di sini (ATS check, keyword analysis)

        # 5. Siapkan respons JSON untuk Frontend
        analysis_result = {
            "match_score": score,
            "message": "Analisis berhasil."
            # Nanti kita tambahkan hasil lain di sini
        }

        # (Opsional - Langkah Lanjutan) Simpan hasil analisis ke database
        # Anda akan membuat fungsi database.save_analysis(...)

        return jsonify(analysis_result), 200

    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500
    finally:
        # Hapus file sementara setelah selesai
        if os.path.exists(file_path):
            os.remove(file_path)