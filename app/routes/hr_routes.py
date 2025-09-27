from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

from app.services.cv_parser import extract_text
from app.services.ai_analyzer import parse_candidate_info, calculate_match_score
from app import database


hr_bp = Blueprint('hr_api', __name__, url_prefix='/api/hr')

UPLOAD_FOLDER = 'temp_uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@hr_bp.route('/jobs/<int:job_id>/upload', methods=['POST'])
def upload_and_process_cvs(job_id):
    if 'cv_files' not in request.files:
        return jsonify({"error": "Tidak ada bagian file (cv_files) dalam request"}), 400

    cv_files = request.files.getlist('cv_files')
    job_description = request.form.get('job_description', '')
    
    if not job_description or not cv_files or cv_files[0].filename == '':
        return jsonify({"error": "Deskripsi pekerjaan dan file CV tidak boleh kosong"}), 400

    processed_count = 0
    errors = []

    for cv_file in cv_files:
        filename = secure_filename(cv_file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            cv_file.save(file_path)

            # 1. Panggil Servis Parser
            cv_text = extract_text(file_path)
            if not cv_text:
                raise ValueError("Teks tidak dapat diekstrak.")

            # 2. Panggil Servis AI Analyzer
            structured_profile = parse_candidate_info(cv_text)
            score = calculate_match_score(cv_text, job_description)

            # Siapkan data untuk disimpan
            candidate_data = {
                'original_filename': filename,
                'storage_path': file_path, # Anda bisa ganti ini dengan path permanen nanti
                'name': structured_profile.get('name'),
                'email': structured_profile.get('email'),
                'phone': structured_profile.get('phone'),
                'score': score,
                'structured_profile': structured_profile # Ini akan diubah jadi JSON
            }
            
            # 3. Panggil Servis Database
            database.save_candidate(job_id, candidate_data)
            processed_count += 1

        except Exception as e:
            errors.append(f"Gagal memproses file {filename}: {str(e)}")
        finally:
            # Selalu hapus file sementara setelah selesai diproses
            if os.path.exists(file_path):
                os.remove(file_path)

    return jsonify({
        "message": "Pemrosesan CV selesai.",
        "success_count": processed_count,
        "error_count": len(errors),
        "errors": errors
    }), 200


@hr_bp.route('/jobs/<int:job_id>/candidates', methods=['GET'])
def get_ranked_candidates(job_id):
    try:
        candidates = database.get_all_candidates_for_job(job_id)
        return jsonify(candidates)
    except Exception as e:
        return jsonify({"error": "Gagal mengambil data dari database", "details": str(e)}), 500

# Endpoint untuk profil detail (lakukan hal yang sama)
@hr_bp.route('/candidates/<int:candidate_id>', methods=['GET'])
def get_candidate_detail(candidate_id):
    # Di sini Anda akan membuat fungsi database.get_candidate_by_id(candidate_id)
    # Untuk sekarang, kita bisa fokus pada daftar ranking dulu.
    pass