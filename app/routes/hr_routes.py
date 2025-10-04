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
    # Bagian ini tetap sama (mengambil file, data job, inisialisasi report)
    cv_files = request.files.getlist('cv_files')
    job = database.get_job_by_id(job_id)
    if not job:
        return jsonify({"error": "Job ID tidak ditemukan"}), 404
    job_requirements = {'min_gpa': job.get('min_gpa'), 'min_experience': job.get('min_experience')}
    job_description = job.get('job_description', '')
    report = {"passed_count": 0, "rejected_count": 0, "rejection_details": {}}

    for cv_file in cv_files:
        filename = secure_filename(cv_file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        try:
            cv_file.save(file_path)
            cv_text = extract_text(file_path)

            # === PERUBAHAN POIN 1: Panggil SATU fungsi saja ===
            # Kita tidak lagi memanggil extract_prescreen_data.
            # parse_candidate_info sekarang mengambil SEMUA data (nama, email, ipk, pengalaman).
            structured_profile = parse_candidate_info(cv_text)
            
            rejection_reason = None
            
            # === PERUBAHAN POIN 2: Filter menggunakan hasil structured_profile ===
            candidate_gpa = structured_profile.get('gpa')
            candidate_experience = structured_profile.get('total_experience')

            # Filter berdasarkan IPK
            if job_requirements['min_gpa'] and (not candidate_gpa or candidate_gpa < job_requirements['min_gpa']):
                rejection_reason = f"GPA below minimum requirement ({job_requirements['min_gpa']})"

            # Filter berdasarkan Pengalaman
            elif job_requirements.get('min_experience') and (candidate_experience is None or candidate_experience < job_requirements.get('min_experience')):
                rejection_reason = f"Experience below minimum requirement ({job_requirements.get('min_experience')} years)"

            if rejection_reason:
                # KANDIDAT DITOLAK
                report['rejected_count'] += 1
                report['rejection_details'][rejection_reason] = report['rejection_details'].get(rejection_reason, 0) + 1
                
                # === PERUBAHAN POIN 3: Data yang dikirim ke database ===
                database.save_candidate(job_id, {
                    'original_filename': filename,
                    'name': structured_profile.get('name'),
                    'email': structured_profile.get('email'),
                    'phone': structured_profile.get('phone'),
                    'structured_profile': structured_profile, # Kirim SEMUA hasil parsing
                    'status': 'rejected', 
                    'rejection_reason': rejection_reason
                })
            else:
                # KANDIDAT LOLOS
                report['passed_count'] += 1
                score = calculate_match_score(cv_text, job_description)

                # === PERUBAHAN POIN 3: Data yang dikirim ke database ===
                database.save_candidate(job_id, {
                    'original_filename': filename,
                    'name': structured_profile.get('name'),
                    'email': structured_profile.get('email'),
                    'phone': structured_profile.get('phone'),
                    'score': score,
                    'structured_profile': structured_profile, # Kirim SEMUA hasil parsing
                    'status': 'passed_filter'
                })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    return jsonify(report), 200


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

@hr_bp.route('/jobs', methods=['GET'])
def get_jobs_list():
    """Endpoint untuk mengambil semua data pekerjaan."""
    try:
        jobs = database.get_all_jobs()
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": "Gagal mengambil daftar pekerjaan", "details": str(e)}), 500